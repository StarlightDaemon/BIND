"""
BIND RSS Feed Server

Lightweight Flask server that reads from SQLite and serves:
- RSS 2.0 feed at /feed.xml
- React SPA at /* (served from static/dist/)
- JSON API at /api/*
- Health check at /health
"""

import hmac
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

from src.config_manager import ConfigManager, LiveConfig
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
    log_security_event,
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
        logger.critical(
            "FLASK_SECRET_KEY not set and data dir is not writable — using an "
            "EPHEMERAL key. Sessions reset on every restart, and under gunicorn "
            "EACH worker generates its own key, so sessions/CSRF tokens signed by "
            "one worker are rejected by the others (login appears to fail at "
            "random). Set FLASK_SECRET_KEY or fix data-dir permissions."
        )
        return key


# Live view of config.env for this process (SEC-2): managed keys are read
# through it at request time, so Settings-page changes to e.g. BIND_AUTH_ENABLED
# apply within seconds without a restart. Keys present in the real process
# environment at import time stay pinned for the process lifetime (operator
# contract). config.env is NO LONGER seeded into os.environ (ARCH-2/SEC-2):
# values that merely originated from the file must not shadow later file edits.
live_config = LiveConfig()

# Resolve the secret key through live_config: the key-file location is derived
# from BIND_DB_PATH, which an operator may set only in config.env, not the
# process environment (SEC-6 ordering fix).
app.secret_key = _resolve_secret_key(
    os.path.dirname(os.path.abspath(live_config.get("BIND_DB_PATH")))
)

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
# Startup-only read: Flask copies cookie config at request time, but flipping
# cookie security live would invalidate sessions mid-flight — restart to apply.
app.config["SESSION_COOKIE_SECURE"] = live_config.get("BIND_COOKIE_SECURE").lower() == "true"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=24)


@app.after_request
def _add_security_headers(response: Response) -> Response:
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response


# Startup-only read: the store/data dir cannot move while the process runs.
BIND_DB_PATH = live_config.get("BIND_DB_PATH")
FEED_TITLE = "BIND - Book Indexing Network"
FEED_DESCRIPTION = "Automatically collected audiobook magnet links"
MAX_ITEMS = 100

_data_dir = os.path.dirname(os.path.abspath(BIND_DB_PATH))
tracker_manager = TrackerManager(_data_dir)
store = MagnetStore(BIND_DB_PATH)

ip_allowlist_middleware(app, live_config)


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
    # Guard for None before compare_digest (it raises on None) and use a
    # constant-time comparison to avoid leaking the token via timing.
    if not token or not form_token or not hmac.compare_digest(token, form_token):
        log_security_event("CSRF_FAILED", "-", get_client_ip(request), f"path={request.path}")
        abort(403, description="CSRF token missing or invalid.")


def _validate_csrf_json() -> None:
    token = session.get("csrf_token")
    request_token = request.headers.get("X-CSRF-Token")
    if not token or not request_token or not hmac.compare_digest(token, request_token):
        log_security_event("CSRF_FAILED", "-", get_client_ip(request), f"path={request.path}")
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
        # Read live per request (SEC-2): a Settings-page change to
        # BIND_AUTH_ENABLED applies within seconds, no restart.
        if not live_config.get_bool("BIND_AUTH_ENABLED"):
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

        # Primary signal: the daemon's heartbeat row in the shared SQLite DB —
        # the only channel both processes share in every deployment mode (ARCH-1).
        hb = store.last_heartbeat()
        if hb is not None:
            beat_at = datetime.fromisoformat(hb["beat_at"])
            if beat_at.tzinfo is None:
                beat_at = beat_at.replace(tzinfo=timezone.utc)
            ts = beat_at.timestamp()
            age_s = (datetime.now(timezone.utc) - beat_at).total_seconds()
            if hb["state"] == "disabled":
                return "online", "Scraping disabled", ts
            if age_s <= 90:
                return "online", f"Active ({hb['state']}, beat {int(age_s)}s ago)", ts
            return "offline", f"No heartbeat for {int(age_s)}s", ts

        # Fallback: no heartbeat row (old daemon, or before its first beat).
        # Degrade to the legacy log-mtime heuristic so a new RSS server against an
        # old daemon does not report a dead daemon.
        # REMOVE in the release after daemon heartbeat ships.
        log_path = os.path.join(get_logs_dir(), "bind.log")
        if not os.path.exists(log_path):
            return "unknown", "Log file not found", 0
        mtime = os.path.getmtime(log_path)
        last_active = datetime.fromtimestamp(mtime, tz=timezone.utc)
        diff_minutes = (datetime.now(timezone.utc) - last_active).total_seconds() / 60
        if diff_minutes < (interval * 2) + 5:
            return "online", f"Active (Last job: {int(diff_minutes)}m ago)", mtime
        return "offline", f"Stalled (Last job: {int(diff_minutes)}m ago)", mtime
    except Exception as e:
        logger.warning("Error checking daemon status: %s", e)
        return "unknown", "Error checking daemon status", 0


# =============================================================================
# Non-UI routes (unchanged)
# =============================================================================


@app.route("/feed.xml")
def feed() -> Response:
    current_trackers = tracker_manager.get_trackers()
    rows = store.recent(limit=MAX_ITEMS)
    magnets = _enrich(rows, current_trackers)
    base_url = live_config.get("BASE_URL") or f"http://{request.host}"

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
    # DB-only: a container HEALTHCHECK target must not depend on a third party's
    # reachability or block on a 10s outbound probe. The ABB probe moved to
    # /api/stats (authenticated, polled). (DEP-2)
    db_stats = store.stats()
    daemon_status, _, _ = check_daemon_status()
    return {
        "status": "ok",
        "magnet_count": db_stats["total"],
        "last_date": db_stats["last_date"],
        "daemon": daemon_status,
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
        # Session-fixation hygiene (SEC-9): drop any pre-auth session before
        # marking authenticated. Then rotate the CSRF token (SEC-8) so a token
        # issued pre-login does not survive privilege elevation.
        session.clear()
        session["authenticated"] = True
        session.permanent = True
        session.pop("csrf_token", None)
        generate_csrf_token()
        return jsonify({"ok": True})
    return jsonify({"error": "Invalid credentials"}), 401


@app.route("/api/logout", methods=["POST"])
def api_logout() -> Any:
    if session.get("authenticated"):
        log_security_event("LOGOUT", "-", get_client_ip(request))
    session.clear()
    return jsonify({"ok": True})


@app.route("/api/me")
def api_me() -> Any:
    auth_enabled = live_config.get_bool("BIND_AUTH_ENABLED")
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
        log_security_event("SETUP_REJECTED", "-", get_client_ip(request), "setup already complete")
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
# JSON API — Magnets
# =============================================================================


@app.route("/api/magnets")
@requires_session_auth
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
    # Same effective view the daemon uses (env-pinned > config.env > default),
    # so the dashboard can never disagree with the daemon about this flag.
    scraping_enabled = live_config.get_bool("SCRAPING_ENABLED")
    # ABB reachability probe (cached 5 min) — relocated here from /health (DEP-2).
    if time.monotonic() > _probe_cache["expires"]:
        _probe_cache["result"] = BindScraper().probe_target()
        _probe_cache["expires"] = time.monotonic() + 300
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
            "target_probe": _probe_cache["result"],
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
    # Start from the stored config so any key not exposed in the UI (e.g.
    # BIND_DB_PATH, BIND_COOKIE_SECURE, future additions) is preserved
    # automatically — no key enumeration required here. (ARCH-4)
    new_config = config_manager.read_config()
    # UI-exposed keys: overlay submitted values (string-coerced and stripped)
    ui_keys = (
        "ABB_URL",
        "SCRAPE_INTERVAL",
        "BIND_PROXY",
        "BASE_URL",
        "CIRCUIT_BREAKER_THRESHOLD",
        "CIRCUIT_BREAKER_COOLDOWN",
        "BIND_PROXIES",
        "BIND_JOB_TIMEOUT",
        "BIND_IP_FILTER",
        "BIND_AUTH_ENABLED",
        "SCRAPING_ENABLED",
    )
    for key in ui_keys:
        if key in data:
            new_config[key] = str(data[key]).strip()
    write_success, write_message = config_manager.write_config(new_config)
    if not write_success:
        return jsonify({"ok": False, "message": write_message}), 400
    # Scraping/auth/IP-filter flags are read live; keys like ABB_URL and
    # SCRAPE_INTERVAL are read at daemon startup and still need this restart
    # (which only works under systemd — hence the honest fallback message).
    live_note = (
        "Scraping, auth, and IP-filter changes apply within seconds; "
        "other settings apply on daemon restart."
    )
    restart_success, restart_message = config_manager.restart_daemon()
    if restart_success:
        return jsonify(
            {
                "ok": True,
                "message": f"Configuration saved. {live_note} Daemon restarted successfully.",
            }
        )
    return jsonify(
        {"ok": True, "message": f"Configuration saved. {live_note} Note: {restart_message}"}
    )


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
    # The config write above is sufficient: the daemon reads SCRAPING_ENABLED
    # live and picks the change up within one loop tick (ARCH-2). No restart.
    # COMPAT(remove after vNEXT): a pre-live-config daemon only notices an
    # enable via this sentinel. The current daemon deletes it at startup and
    # ignores it at runtime, so the write is harmless to new daemons and
    # functional for old ones during the one-release upgrade window.
    enable_file = os.path.join(get_data_dir(), ".enable-scraping")
    try:
        pathlib.Path(enable_file).touch()
    except OSError as e:
        logger.warning("Could not write enable sentinel: %s", e)
    return jsonify(
        {"ok": True, "message": "Scraping enabled. The daemon will start within a few seconds."}
    )


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
    READ_WINDOW = 512 * 1024  # 512 KB tail window
    logs: list[str] = []
    if os.path.exists(filepath):
        try:
            with open(filepath, encoding="utf-8", errors="replace") as f:
                f.seek(0, 2)  # seek to end
                size = f.tell()
                offset = max(0, size - READ_WINDOW)
                f.seek(offset)
                raw = f.read()
                # When we seeked into the middle of a file, the first "line" is
                # likely a partial line — discard it.
                if offset > 0:
                    newline_pos = raw.find("\n")
                    if newline_pos != -1:
                        raw = raw[newline_pos + 1 :]
                all_lines = raw.splitlines()
                logs = [line.strip() for line in reversed(all_lines[-MAX_LINES:])]
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
    try:
        if os.path.exists(trigger_file):
            # A trigger older than 2× the scrape interval was left by a daemon
            # that never consumed it (dead or restarted) — replace it instead
            # of 409-blocking manual scrapes forever (ARCH-3).
            stale_after_s = 2 * live_config.get_int("SCRAPE_INTERVAL") * 60
            age_s = time.time() - os.path.getmtime(trigger_file)
            if age_s <= stale_after_s:
                return jsonify({"ok": False, "message": "A trigger is already pending."}), 409
            pathlib.Path(trigger_file).touch()
            return jsonify(
                {
                    "ok": True,
                    "message": "Stale trigger from a previous daemon replaced — "
                    "scrape job triggered.",
                }
            )
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
