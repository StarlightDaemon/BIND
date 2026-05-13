"""
BIND RSS Feed Server

Lightweight Flask server that reads from SQLite and serves:
- RSS 2.0 feed at /feed.xml
- Simple web UI at /
- Health check at /health
"""

import logging
import os
import secrets
from datetime import datetime, timezone
from typing import Any, cast
from xml.sax.saxutils import escape

from flask import Flask, Response, abort, redirect, render_template, request, session

from src.config_manager import ConfigManager
from src.core.magnet import generate_magnet
from src.core.storage import MagnetStore
from src.core.tracker_manager import TrackerManager
from src.security import (
    change_password,
    get_security_log_path,
    ip_allowlist_middleware,
    is_setup_complete,
    requires_auth,
    save_credentials,
)

logger = logging.getLogger("rss_server")

_current_dir = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, template_folder=os.path.join(_current_dir, "templates"))


def _resolve_secret_key(data_dir: str) -> str:
    env_key = os.getenv("FLASK_SECRET_KEY")
    if env_key:
        return env_key
    key_file = os.path.join(data_dir, ".secret_key")
    try:
        if os.path.isfile(key_file):
            stored = open(key_file).read().strip()
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


def validate_csrf_token() -> None:
    if request.method == "POST":
        token = session.get("csrf_token")
        form_token = request.form.get("csrf_token")
        if not token or token != form_token:
            abort(403, description="CSRF token missing or invalid.")


app.jinja_env.globals["csrf_token"] = generate_csrf_token


@app.before_request
def check_setup_required() -> Any:
    if request.path in ["/setup", "/health"]:
        return None
    if not is_setup_complete():
        return redirect("/setup")
    return None


@app.before_request
def csrf_protect() -> None:
    if request.method == "POST":
        validate_csrf_token()


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
    """Map MagnetStore rows to the shape templates and RSS feed expect."""
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


# =============================================================================
# Routes
# =============================================================================


@app.route("/")
def index() -> str:
    current_trackers = tracker_manager.get_trackers()
    rows = store.recent(limit=20)
    magnets = _enrich(rows, current_trackers)
    total_count = store.stats()["total"]
    return render_template(
        "index.html",
        magnets=magnets,
        magnet_count=total_count,
        display_count=len(magnets),
    )


@app.route("/magnets")
def magnets_view() -> str:
    import math

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

    return render_template(
        "magnets.html",
        magnets=magnets,
        query=query,
        page=page,
        total_pages=total_pages,
        total_count=total_count,
    )


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
            <enclosure url="{magnet_escaped}" type="application/x-bittorrent" />
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
    db_stats = store.stats()
    return {
        "status": "ok",
        "magnet_count": db_stats["total"],
        "db_path": BIND_DB_PATH,
        "last_date": db_stats["last_date"],
    }


config_manager = ConfigManager()


@app.route("/settings", methods=["GET", "POST"])
@requires_auth
def settings() -> str:
    message = None
    success = False

    if request.method == "POST":
        new_config = {
            "ABB_URL": request.form.get("ABB_URL", "").strip(),
            "SCRAPE_INTERVAL": request.form.get("SCRAPE_INTERVAL", "60").strip(),
            "BIND_PROXY": request.form.get("BIND_PROXY", "").strip(),
            "BASE_URL": request.form.get("BASE_URL", "").strip(),
            "CIRCUIT_BREAKER_THRESHOLD": request.form.get("CIRCUIT_BREAKER_THRESHOLD", "3").strip(),
            "CIRCUIT_BREAKER_COOLDOWN": request.form.get("CIRCUIT_BREAKER_COOLDOWN", "300").strip(),
            "BIND_PROXIES": request.form.get("BIND_PROXIES", "").strip(),
            "BIND_JOB_TIMEOUT": request.form.get("BIND_JOB_TIMEOUT", "3600").strip(),
            "BIND_IP_FILTER": request.form.get("BIND_IP_FILTER", "true").strip(),
            "BIND_AUTH_ENABLED": request.form.get("BIND_AUTH_ENABLED", "true").strip(),
        }
        write_success, write_message = config_manager.write_config(new_config)
        if write_success:
            restart_success, restart_message = config_manager.restart_daemon()
            if restart_success:
                message = "Configuration saved. Daemon restarted successfully."
                success = True
            else:
                message = f"Configuration saved. Note: {restart_message}"
                success = True
        else:
            message = write_message

    config = config_manager.read_config()
    trackers = tracker_manager.get_trackers()
    return render_template(
        "settings.html",
        config=config,
        trackers_text="\n".join(trackers),
        message=message,
        success=success,
    )


@app.route("/settings/trackers", methods=["POST"])
@requires_auth
def settings_trackers() -> str:
    trackers_text = request.form.get("trackers", "").strip()
    try:
        tracker_manager.set_trackers_from_text(trackers_text)
        message = "Trackers updated successfully."
        success = True
    except Exception as e:
        message = f"Failed to update trackers: {e}"
        success = False

    config = config_manager.read_config()
    trackers = tracker_manager.get_trackers()
    return render_template(
        "settings.html",
        config=config,
        trackers_text="\n".join(trackers),
        message=message,
        success=success,
    )


@app.route("/logs")
@requires_auth
def logs_view() -> str:
    log_type = request.args.get("log", "security")

    if log_type == "daemon":
        filename = "bind.log"
        filepath = os.path.join(os.getcwd(), filename)
    else:
        log_type = "security"
        filename = "security.log"
        filepath = get_security_log_path()

    logs = []
    MAX_LINES = 1000

    if os.path.exists(filepath):
        try:
            with open(filepath, encoding="utf-8") as f:
                lines = f.readlines()
                logs = [line.strip() for line in reversed(lines[-MAX_LINES:])]
        except Exception as e:
            logs = [f"Error reading log file: {e}"]
    else:
        logs = [f"Log file not found: {filepath}"]

    return render_template(
        "logs.html", current_log=log_type, log_file=filename, logs=logs, line_count=len(logs)
    )


@app.route("/setup", methods=["GET", "POST"])
def setup() -> Any:
    if is_setup_complete():
        return redirect("/")

    error = None
    username = ""

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if password != confirm_password:
            error = "Passwords do not match."
        else:
            success, message = save_credentials(username, password)
            if success:
                return redirect("/")
            else:
                error = message

    return render_template("setup.html", error=error, username=username)


@app.route("/settings/password", methods=["POST"])
@requires_auth
def change_password_route() -> str:
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_new_password", "")

    password_message = None
    password_success = False

    if new_password != confirm_password:
        password_message = "New passwords do not match."
    else:
        success, message = change_password(current_password, new_password)
        password_message = message
        password_success = success

    config = config_manager.read_config()
    return render_template(
        "settings.html",
        config=config,
        message=None,
        success=False,
        password_message=password_message,
        password_success=password_success,
    )


def check_daemon_status() -> tuple[str, str, float]:
    try:
        config = config_manager.read_config()
        interval = int(config.get("SCRAPE_INTERVAL", 60))
        log_path = os.path.join(os.getcwd(), "bind.log")

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


@app.route("/api/stats")
@requires_auth
def api_stats() -> dict[str, Any]:
    status, message, _ = check_daemon_status()
    db_stats = store.stats()
    current_trackers = tracker_manager.get_trackers()
    recent_rows = store.recent(limit=20)
    recent_magnets = _enrich(recent_rows, current_trackers)

    return {
        "system_status": status,
        "status_message": message,
        "magnet_count": db_stats["total"],
        "recent_magnets": recent_magnets,
        "server_time": datetime.now(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z"),
    }
