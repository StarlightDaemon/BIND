"""
BIND RSS Feed Server

Lightweight Flask server that reads from SQLite and serves:
- RSS 2.0 feed at /feed.xml
- React SPA at /* (served from static/dist/)
- JSON API at /api/*
- Health check at /health
"""

import logging
import math
import os
import pathlib
import secrets
import subprocess
import time
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, TypeVar, cast
from xml.sax.saxutils import escape

from flask import Flask, Response, abort, jsonify, redirect, request, send_from_directory, session

from src.config_manager import ConfigManager
from src.core.magnet import generate_magnet
from src.core.scraper import BindScraper
from src.core.storage import MagnetStore
from src.core.tracker_manager import TrackerManager
from src.security import (
    change_password,
    get_client_ip,
    get_data_dir,
    get_logs_dir,
    get_security_log_path,
    ip_allowlist_middleware,
    is_setup_complete,
    save_credentials,
    verify_credentials,
)

logger = logging.getLogger("rss_server")

_probe_cache: dict[str, Any] = {"result": None, "expires": 0.0}
_current_dir = os.path.dirname(os.path.abspath(__file__))
_SPA_DIST = os.path.join(_current_dir, "static", "dist")
_FRONTEND_DIR = os.path.join(os.path.dirname(_current_dir), "frontend")


def _run_npm(args: list[str], cwd: str) -> bool:
    try:
        result = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error("npm %s failed:\n%s", " ".join(args[1:]), result.stderr or result.stdout)
            return False
        return True
    except FileNotFoundError:
        logger.error("'npm' not found — install Node.js or run: cd frontend && npm run build")
        return False
    except Exception as e:
        logger.error("Frontend build error: %s", e)
        return False


def _build_frontend() -> None:
    if os.path.isfile(os.path.join(_SPA_DIST, "index.html")):
        return
    if not os.path.isdir(_FRONTEND_DIR):
        logger.warning(
            "Frontend source directory not found at %s — skipping auto-build", _FRONTEND_DIR
        )
        return
    if not os.path.isdir(os.path.join(_FRONTEND_DIR, "node_modules")):
        logger.info("Installing frontend dependencies (first run)...")
        if not _run_npm(["npm", "install"], _FRONTEND_DIR):
            return
    logger.info("Frontend not built — running 'npm run build' (this may take ~30s)...")
    if _run_npm(["npm", "run", "build"], _FRONTEND_DIR):
        logger.info("Frontend build complete.")


_build_frontend()

app = Flask(__name__, template_folder=os.path.join(_current_dir, "templates"))


def _resolve_secret_key(data_dir: str) -> str:
    env_key = os.getenv("FLASK_SECRET_KEY")
    if env_key:
        return env_key
    key_file = os.path.join(data_dir, ".secret_key")
    try:
        if os.path.isfile(key_file):
            with open(key_file, encoding="utf-8") as _kf:
                stored = _kf.read().strip()
            if stored:
                return stored
        key = secrets.token_hex(32)
        os.makedirs(data_dir, exist_ok=True)
        with open(key_file, "w") as f:
            f.write(key)
        os.chmod(key_file, 0o600)
        logger.warning(
            "FLASK_SECRET_KEY not set — auto-generated and saved to %s. "
            "Set FLASK_SECRET_KEY env var to pin this value.",
            key_file,
        )
        return key
    except OSError:
        key = secrets.token_hex(32)
        logger.warning(
            "FLASK_SECRET_KEY not set and data dir is not writable — "
            "using ephemeral key; sessions reset on every restart."
        )
        return key


app.secret_key = _resolve_secret_key(
    os.path.dirname(os.path.abspath(os.getenv("BIND_DB_PATH", "data/bind.db")))
)

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=24)


@app.after_request
def _add_security_headers(response: Response) -> Response:
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response


try:
    _config_mgr = ConfigManager()
    _config = _config_mgr.read_config()
    for _key, _value in _config.items():
        if _key not in os.environ:
            os.environ[_key] = str(_value)
except Exception as e:
    logger.warning(f"Failed to load config.env: {e}")

BIND_DB_PATH = os.getenv("BIND_DB_PATH", "data/bind.db")
FEED_TITLE = "BIND - Book Indexing Network"
FEED_DESCRIPTION = "Automatically collected audiobook magnet links"
MAX_ITEMS = 100

_data_dir = os.path.dirname(os.path.abspath(BIND_DB_PATH))
tracker_manager = TrackerManager(_data_dir)
store = MagnetStore(BIND_DB_PATH)

ip_allowlist_middleware(app)


# =============================================================================
# CSRF Protection
# =============================================================================


def generate_csrf_token() -> str:
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return cast(str, session["csrf_token"])


def _validate_csrf_form() -> None:
    token = session.get("csrf_token")
    form_token = request.form.get("csrf_token")
    if not token or token != form_token:
        abort(403, description="CSRF token missing or invalid.")


def _validate_csrf_json() -> None:
    token = session.get("csrf_token")
    request_token = request.headers.get("X-CSRF-Token")
    if not token or token != request_token:
        abort(403, description="CSRF token missing or invalid.")


app.jinja_env.globals["csrf_token"] = generate_csrf_token


@app.before_request
def check_setup_required() -> Any:
    # API calls, static files, and feed/health manage their own state
    if (
        request.path.startswith("/api/")
        or request.path.startswith("/static/")
        or request.path in ["/health", "/feed.xml"]
    ):
        return None
    # React SPA handles the client-side setup redirect; this is a server-side safety net
    if request.path not in ["/setup"] and not is_setup_complete():
        return redirect("/setup")
    return None


@app.before_request
def csrf_protect() -> None:
    if request.method != "POST":
        return
    if request.path.startswith("/api/"):
        _validate_csrf_json()
    else:
        _validate_csrf_form()


# =============================================================================
# Auth decorators
# =============================================================================

F = TypeVar("F", bound=Callable[..., Any])


def requires_session_auth(f: F) -> F:
    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        if os.getenv("BIND_AUTH_ENABLED", "true").lower() == "false":
            return f(*args, **kwargs)
        if not session.get("authenticated"):
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)

    return cast(F, decorated)


# =============================================================================
# Helpers
# =============================================================================


def _date_to_rfc2822(date_str: str) -> str:
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return dt.strftime("%a, %d %b %Y %H:%M:%S GMT")
    except ValueError:
        return datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")


def _enrich(rows: list[dict[str, Any]], trackers: list[str]) -> list[dict[str, Any]]:
    enriched = []
    for r in rows:
        enriched.append(
            {
                **r,
                "hash": r["info_hash"],
                "date": r["collected_date"],
                "magnet": generate_magnet(r["info_hash"], r["title"], trackers),
            }
        )
    return enriched


config_manager = ConfigManager()


def check_daemon_status() -> tuple[str, str, float]:
    try:
        config = config_manager.read_config()
        interval = int(config.get("SCRAPE_INTERVAL", 60))
        log_path = os.path.join(get_logs_dir(), "bind.log")

        if not os.path.exists(log_path):
            return "unknown", "Log file not found", 0

        mtime = os.path.getmtime(log_path)
        last_active = datetime.fromtimestamp(mtime, tz=timezone.utc)
        now = datetime.now(timezone.utc)
        diff_minutes = (now - last_active).total_seconds() / 60

        if diff_minutes < (interval * 2) + 5:
            return "online", f"Active (Last job: {int(diff_minutes)}m ago)", mtime
        else:
            return "offline", f"Stalled (Last job: {int(diff_minutes)}m ago)", mtime
    except Exception as e:
        return "unknown", f"Error checking status: {str(e)}", 0


# =============================================================================
# Non-UI routes (unchanged)
# =============================================================================


@app.route("/feed.xml")
def feed() -> Response:
    current_trackers = tracker_manager.get_trackers()
    rows = store.recent(limit=MAX_ITEMS)
    magnets = _enrich(rows, current_trackers)
    base_url = os.getenv("BASE_URL") or f"http://{request.host}"

    rss_items = []
    for magnet in magnets:
        pub_date = _date_to_rfc2822(magnet["date"])
        guid = magnet["hash"]
        magnet_escaped = escape(magnet["magnet"])
        title_safe = magnet["title"].replace("]]>", "]]]]><![CDATA[>")

        item = f"""
        <item>
            <title><![CDATA[{title_safe}]]></title>
            <link>{magnet_escaped}</link>
            <guid isPermaLink="false">{guid}</guid>
            <pubDate>{pub_date}</pubDate>
            <description><![CDATA[Magnet link for: {title_safe}]]></description>
        </item>
        """
        rss_items.append(item.strip())

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
    <channel>
        <title>{escape(FEED_TITLE)}</title>
        <link>{escape(base_url)}</link>
        <description>{escape(FEED_DESCRIPTION)}</description>
        <language>en-us</language>
        <lastBuildDate>{datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")}</lastBuildDate>
        <atom:link href="{escape(base_url)}/feed.xml" rel="self" type="application/rss+xml" />

        {"".join(rss_items)}
    </channel>
</rss>
"""
    return Response(rss_xml, mimetype="application/rss+xml")


@app.route("/health")
def health() -> dict[str, Any]:
    if time.monotonic() > _probe_cache["expires"]:
        _probe_cache["result"] = BindScraper().probe_target()
        _probe_cache["expires"] = time.monotonic() + 300
    db_stats = store.stats()
    return {
        "status": "ok",
        "magnet_count": db_stats["total"],
        "last_date": db_stats["last_date"],
        "target_probe": _probe_cache["result"],
    }


# =============================================================================
# JSON API — Auth
# =============================================================================


@app.route("/api/csrf-token")
def api_csrf_token() -> Any:
    return jsonify({"csrf_token": generate_csrf_token()})


@app.route("/api/login", methods=["POST"])
def api_login() -> Any:
    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")
    if verify_credentials(username, password, ip=get_client_ip(request)):
        session["authenticated"] = True
        session.permanent = True
        return jsonify({"ok": True})
    return jsonify({"error": "Invalid credentials"}), 401


@app.route("/api/logout", methods=["POST"])
def api_logout() -> Any:
    session.clear()
    return jsonify({"ok": True})


@app.route("/api/me")
def api_me() -> Any:
    auth_enabled = os.getenv("BIND_AUTH_ENABLED", "true").lower() != "false"
    return jsonify(
        {
            "authenticated": not auth_enabled or bool(session.get("authenticated")),
            "auth_enabled": auth_enabled,
        }
    )


# =============================================================================
# JSON API — Setup
# =============================================================================


@app.route("/api/setup/status")
def api_setup_status() -> Any:
    return jsonify({"setup_complete": is_setup_complete()})


@app.route("/api/setup", methods=["POST"])
def api_setup() -> Any:
    if is_setup_complete():
        return jsonify({"error": "Setup already complete"}), 400
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    confirm_password = data.get("confirm_password", "")
    if password != confirm_password:
        return jsonify({"error": "Passwords do not match."}), 400
    success, message = save_credentials(username, password, ip=get_client_ip(request))
    if success:
        # Write initial config with scraping disabled so the user opts in explicitly
        initial_config = config_manager.read_config()
        initial_config["SCRAPING_ENABLED"] = "false"
        write_ok, write_msg = config_manager.write_config(initial_config)
        if not write_ok:
            return jsonify(
                {"error": f"Setup succeeded but config could not be written: {write_msg}"}
            ), 500
        return jsonify({"ok": True})
    return jsonify({"error": message}), 400


# =============================================================================
# JSON API — Dashboard & Magnets (public)
# =============================================================================


@app.route("/api/dashboard")
def api_dashboard() -> Any:
    current_trackers = tracker_manager.get_trackers()
    rows = store.recent(limit=20)
    magnets = _enrich(rows, current_trackers)
    total_count = store.stats()["total"]
    status, message, _ = check_daemon_status()
    return jsonify(
        {
            "magnets": magnets,
            "magnet_count": total_count,
            "display_count": len(magnets),
            "system_status": status,
            "status_message": message,
        }
    )


@app.route("/api/magnets")
def api_magnets() -> Any:
    query = request.args.get("q", "").strip()
    try:
        page = max(1, int(request.args.get("page", 1)))
    except ValueError:
        page = 1
    per_page = 50
    current_trackers = tracker_manager.get_trackers()
    rows, total_count = store.search(query=query or None, page=page, per_page=per_page)
    magnets = _enrich(rows, current_trackers)
    total_pages = math.ceil(total_count / per_page) if total_count else 1
    return jsonify(
        {
            "magnets": magnets,
            "query": query,
            "page": page,
            "total_pages": total_pages,
            "total_count": total_count,
        }
    )


@app.route("/api/stats")
@requires_session_auth
def api_stats() -> Any:
    status, message, _ = check_daemon_status()
    db_stats = store.stats()
    current_trackers = tracker_manager.get_trackers()
    recent_rows = store.recent(limit=20)
    recent_magnets = _enrich(recent_rows, current_trackers)
    scraping_enabled = (
        config_manager.read_config().get("SCRAPING_ENABLED", "true").lower() != "false"
    )
    return jsonify(
        {
            "system_status": status,
            "status_message": message,
            "magnet_count": db_stats["total"],
            "recent_magnets": recent_magnets,
            "server_time": datetime.now(timezone.utc)
            .isoformat(timespec="microseconds")
            .replace("+00:00", "Z"),
            "scraping_enabled": scraping_enabled,
        }
    )


# =============================================================================
# JSON API — Metrics (auth required)
# =============================================================================


@app.route("/api/metrics")
@requires_session_auth
def api_metrics() -> Any:
    db_stats = store.stats()
    runs = store.scrape_runs(limit=30)
    total_runs = len(runs)
    success_count = sum(1 for r in runs if r[1] == "success")
    success_rate = round(success_count / total_runs * 100) if total_runs else None
    runs_out = [{"run_at": r[0], "result": r[1], "new_items": r[2], "duration": r[3]} for r in runs]
    return jsonify(
        {
            "stats": db_stats,
            "runs": runs_out,
            "success_rate": success_rate,
            "daily_counts": store.daily_counts(),
            "now": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
    )


# =============================================================================
# JSON API — Settings (auth required)
# =============================================================================


@app.route("/api/settings", methods=["GET"])
@requires_session_auth
def api_settings_get() -> Any:
    config = config_manager.read_config()
    trackers = tracker_manager.get_trackers()
    return jsonify(
        {
            "config": config,
            "trackers_text": "\n".join(trackers),
        }
    )


@app.route("/api/settings", methods=["POST"])
@requires_session_auth
def api_settings_post() -> Any:
    data = request.get_json(silent=True) or {}
    new_config = {
        "ABB_URL": str(data.get("ABB_URL", "")).strip(),
        "SCRAPE_INTERVAL": str(data.get("SCRAPE_INTERVAL", "60")).strip(),
        "BIND_PROXY": str(data.get("BIND_PROXY", "")).strip(),
        "BASE_URL": str(data.get("BASE_URL", "")).strip(),
        "CIRCUIT_BREAKER_THRESHOLD": str(data.get("CIRCUIT_BREAKER_THRESHOLD", "3")).strip(),
        "CIRCUIT_BREAKER_COOLDOWN": str(data.get("CIRCUIT_BREAKER_COOLDOWN", "300")).strip(),
        "BIND_PROXIES": str(data.get("BIND_PROXIES", "")).strip(),
        "BIND_JOB_TIMEOUT": str(data.get("BIND_JOB_TIMEOUT", "3600")).strip(),
        "BIND_IP_FILTER": str(data.get("BIND_IP_FILTER", "true")).strip(),
        "BIND_AUTH_ENABLED": str(data.get("BIND_AUTH_ENABLED", "true")).strip(),
        "SCRAPING_ENABLED": str(data.get("SCRAPING_ENABLED", "true")).strip(),
    }
    write_success, write_message = config_manager.write_config(new_config)
    if not write_success:
        return jsonify({"ok": False, "message": write_message}), 400
    restart_success, restart_message = config_manager.restart_daemon()
    if restart_success:
        return jsonify(
            {"ok": True, "message": "Configuration saved. Daemon restarted successfully."}
        )
    return jsonify({"ok": True, "message": f"Configuration saved. Note: {restart_message}"})


@app.route("/api/scraping/enable", methods=["POST"])
@requires_session_auth
def api_scraping_enable() -> Any:
    current = config_manager.read_config()
    if current.get("SCRAPING_ENABLED", "true").lower() != "false":
        return jsonify({"ok": True, "message": "Scraping is already enabled."})
    current["SCRAPING_ENABLED"] = "true"
    write_success, write_message = config_manager.write_config(current)
    if not write_success:
        return jsonify({"ok": False, "message": write_message}), 400
    # Signal the running daemon directly via sentinel file (works in Docker/non-systemd).
    enable_file = os.path.join(get_data_dir(), ".enable-scraping")
    try:
        pathlib.Path(enable_file).touch()
    except OSError as e:
        logger.warning("Could not write enable sentinel: %s", e)
    # Also attempt a systemd restart for managed environments.
    restart_success, _ = config_manager.restart_daemon()
    if restart_success:
        return jsonify({"ok": True, "message": "Scraping enabled. Daemon restarted."})
    return jsonify({"ok": True, "message": "Scraping enabled. The daemon is starting up."})


@app.route("/api/settings/trackers", methods=["POST"])
@requires_session_auth
def api_settings_trackers() -> Any:
    data = request.get_json(silent=True) or {}
    trackers_text = data.get("trackers", "").strip()
    try:
        tracker_manager.set_trackers_from_text(trackers_text)
        return jsonify({"ok": True, "message": "Trackers updated successfully."})
    except Exception as e:
        return jsonify({"ok": False, "message": f"Failed to update trackers: {e}"}), 400


@app.route("/api/settings/password", methods=["POST"])
@requires_session_auth
def api_settings_password() -> Any:
    data = request.get_json(silent=True) or {}
    current_password = data.get("current_password", "")
    new_password = data.get("new_password", "")
    confirm_password = data.get("confirm_new_password", "")
    if new_password != confirm_password:
        return jsonify({"ok": False, "message": "New passwords do not match."}), 400
    success, message = change_password(current_password, new_password, ip=get_client_ip(request))
    if success:
        return jsonify({"ok": True, "message": message})
    return jsonify({"ok": False, "message": message}), 400


# =============================================================================
# JSON API — Logs (auth required)
# =============================================================================


@app.route("/api/logs")
@requires_session_auth
def api_logs() -> Any:
    log_type = request.args.get("log", "security")
    if log_type == "daemon":
        filename = "bind.log"
        filepath = os.path.join(get_logs_dir(), filename)
    else:
        log_type = "security"
        filename = "security.log"
        filepath = get_security_log_path()

    MAX_LINES = 1000
    logs: list[str] = []
    if os.path.exists(filepath):
        try:
            with open(filepath, encoding="utf-8") as f:
                lines = f.readlines()
                logs = [line.strip() for line in reversed(lines[-MAX_LINES:])]
        except Exception as e:
            logs = [f"Error reading log file: {e}"]
    else:
        logs = [f"Log file not found: {filepath}"]

    return jsonify(
        {
            "logs": logs,
            "current_log": log_type,
            "log_file": filename,
            "line_count": len(logs),
        }
    )


# =============================================================================
# JSON API — Manual scrape trigger (auth required)
# =============================================================================


@app.route("/api/trigger-scrape", methods=["POST"])
@requires_session_auth
def api_trigger_scrape() -> Any:
    trigger_file = os.path.join(_data_dir, ".trigger")
    if os.path.exists(trigger_file):
        return jsonify({"ok": False, "message": "A trigger is already pending."}), 409
    try:
        pathlib.Path(trigger_file).touch()
        return jsonify({"ok": True, "message": "Scrape job triggered — results in ~60s."})
    except OSError as e:
        return jsonify({"ok": False, "message": f"Could not write trigger file: {e}"}), 500


# =============================================================================
# SPA catch-all — must be last
# =============================================================================


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def spa_index(path: str) -> Any:
    spa_html = os.path.join(_SPA_DIST, "index.html")
    if os.path.isfile(spa_html):
        return send_from_directory(_SPA_DIST, "index.html")
    return (
        "Frontend not built. Run: cd frontend && npm run build",
        503,
        {"Content-Type": "text/plain"},
    )
