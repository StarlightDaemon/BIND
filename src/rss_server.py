"""
BIND RSS Feed Server

Lightweight Flask server that reads magnets.txt and serves it as:
- RSS 2.0 feed at /feed.xml
- Simple web UI at /
- Health check at /health
"""

import fcntl
import glob
import math
import os
import re
import secrets
from datetime import datetime, timezone
from typing import Any, cast
from xml.sax.saxutils import escape

from flask import Flask, Response, abort, redirect, render_template, request, session

from src.config_manager import ConfigManager
from src.core.scraper import BindScraper
from src.core.tracker_manager import TrackerManager
from src.security import (
    change_password,
    get_security_log_path,
    ip_allowlist_middleware,
    is_setup_complete,
    requires_auth,
    save_credentials,
)

# Get the directory where this file is located for template path
_current_dir = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, template_folder=os.path.join(_current_dir, "templates"))

# Secret key for sessions (CSRF tokens)
# Generate a stable key from credentials file path or use random
app.secret_key = os.getenv("FLASK_SECRET_KEY", secrets.token_hex(32))

# Configuration
# [REMEDIATION CONF-01] Load config.env into environment
try:
    _config_mgr = ConfigManager()
    _config = _config_mgr.read_config()
    for _key, _value in _config.items():
        if _key not in os.environ:
            os.environ[_key] = str(_value)
except Exception as e:
    print(f"Warning: Failed to load config.env: {e}")

# Configuration
MAGNETS_DIR = os.getenv("MAGNETS_DIR", "data/magnets")

# [REMEDIATION RUNTIME-01] Legacy Fallback Support
if MAGNETS_DIR == "data/magnets" and not os.path.exists(MAGNETS_DIR) and os.path.exists("magnets"):
    print("WARNING: Canonical directory 'data/magnets/' not found, but legacy 'magnets/' exists.")
    print("FALLBACK: Using legacy 'magnets/' directory. Please migrate to 'data/magnets/'.")
    MAGNETS_DIR = "magnets"
FEED_TITLE = "BIND - Book Indexing Network"
FEED_DESCRIPTION = "Automatically collected audiobook magnet links"
MAX_ITEMS = 100

# Initialize Tracker Manager
tracker_manager = TrackerManager(MAGNETS_DIR)

# Register security middleware
ip_allowlist_middleware(app)


# =============================================================================
# CSRF Protection
# =============================================================================


def generate_csrf_token() -> str:
    """Generate or retrieve CSRF token from session."""
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return cast(str, session["csrf_token"])


def validate_csrf_token() -> None:
    """Validate CSRF token on POST requests."""
    if request.method == "POST":
        token = session.get("csrf_token")
        form_token = request.form.get("csrf_token")

        if not token or token != form_token:
            abort(403, description="CSRF token missing or invalid.")


# Make csrf_token available to all templates
app.jinja_env.globals["csrf_token"] = generate_csrf_token


# Setup redirect middleware
@app.before_request
def check_setup_required() -> Any:
    """Redirect to setup if first-time setup not complete."""
    # Allow setup route and static assets without setup
    if request.path in ["/setup", "/health"]:
        return None

    if not is_setup_complete():
        return redirect("/setup")

    return None


@app.before_request
def csrf_protect() -> None:
    """Validate CSRF token on all POST requests."""
    if request.method == "POST":
        validate_csrf_token()


def parse_magnet_link(magnet_url: str) -> dict[str, Any]:
    """
    Extract information from a magnet link.
    Returns dict with hash, title, and trackers.
    """
    info: dict[str, Any] = {"magnet": magnet_url, "hash": "", "title": "Unknown", "trackers": []}

    # Extract info hash
    hash_match = re.search(r"urn:btih:([a-fA-F0-9]+)", magnet_url)
    if hash_match:
        info["hash"] = hash_match.group(1)

    # Extract display name
    dn_match = re.search(r"[&?]dn=([^&]+)", magnet_url)
    if dn_match:
        # Decode URL encoding (e.g., %3A → :, %2C → ,, %E2%80%99 → ')
        from urllib.parse import unquote_plus

        info["title"] = unquote_plus(dn_match.group(1))

    # Extract trackers
    trackers = re.findall(r"[&?]tr=([^&]+)", magnet_url)
    info["trackers"] = trackers

    return info


def read_magnets() -> list[dict[str, Any]]:
    """
    Read magnets from all date-based files in magnets directory.
    Returns list of magnet info dicts, most recent first.
    """
    magnets = []

    # Create directory if it doesn't exist
    os.makedirs(MAGNETS_DIR, exist_ok=True)

    # Find all magnet files (magnets_YYYY-MM-DD.txt)
    magnet_files = glob.glob(os.path.join(MAGNETS_DIR, "magnets_*.txt"))

    # Sort by filename (date) descending
    magnet_files.sort(reverse=True)

    try:
        for file_path in magnet_files:
            with open(file_path, encoding="utf-8") as f:
                # Acquire shared lock to prevent reading partial writes from daemon
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    lines = f.readlines()
                finally:
                    # Release lock (also auto-released on file close)
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

            for line in lines:
                line = line.strip()
                if line and line.startswith("magnet:"):
                    magnet_info = parse_magnet_link(line)

                    # [V1.2.3] Regenerate magnet link using CURRENT trackers
                    current_trackers = tracker_manager.get_trackers()
                    magnet_info["magnet"] = BindScraper.generate_magnet(
                        magnet_info["hash"], magnet_info["title"], current_trackers
                    )

                    magnets.append(magnet_info)

                    # Limit to MAX_ITEMS
                    if len(magnets) >= MAX_ITEMS:
                        return magnets

        return magnets

    except Exception as e:
        print(f"Error reading magnet files: {e}")
        return []


def search_magnets(
    query: str | None = None, page: int = 1, per_page: int = 50
) -> tuple[list[dict[str, Any]], int]:
    """
    Search and paginate magnets.
    Returns (magnets_page, total_count).
    """
    all_magnets = []

    # Create directory if it doesn't exist
    os.makedirs(MAGNETS_DIR, exist_ok=True)

    # Find all magnet files
    magnet_files = glob.glob(os.path.join(MAGNETS_DIR, "magnets_*.txt"))
    magnet_files.sort(reverse=True)  # Newest first

    # Read ALL magnets (finding the total set)
    # Note: In a larger system, we would index this. For flat files, we read all.
    try:
        for file_path in magnet_files:
            # Extract date from filename for display (magnets_YYYY-MM-DD.txt)
            date_str = "Unknown"
            filename = os.path.basename(file_path)
            if filename.startswith("magnets_") and filename.endswith(".txt"):
                date_str = filename[8:-4]

            with open(file_path, encoding="utf-8") as f:
                # Shared lock for reading
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    lines = f.readlines()
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

            for line in lines:
                line = line.strip()
                if line and line.startswith("magnet:"):
                    # Basic parsing first to check query match (optimization)
                    title = "Unknown"
                    dn_match = re.search(r"[&?]dn=([^&]+)", line)
                    if dn_match:
                        from urllib.parse import unquote_plus

                        title = unquote_plus(dn_match.group(1))

                    # Filter if query exists
                    if query:
                        if query.lower() not in title.lower():
                            continue

                    # If match, fully parse and add
                    info = parse_magnet_link(line)

                    # [V1.2.3] Regenerate magnet link using CURRENT trackers
                    current_trackers = tracker_manager.get_trackers()
                    info["magnet"] = BindScraper.generate_magnet(
                        info["hash"], info["title"], current_trackers
                    )

                    info["date"] = date_str
                    all_magnets.append(info)

    except Exception as e:
        print(f"Error searching magnets: {e}")
        return [], 0

    # Calculate pagination
    total_count = len(all_magnets)
    start = (page - 1) * per_page
    end = start + per_page

    paginated_items = all_magnets[start:end]

    return paginated_items, total_count


@app.route("/")
def index() -> str:
    """Simple web UI showing recent magnet links"""
    magnets = read_magnets()

    # Limit display to 20 most recent magnets
    display_magnets = magnets[:20]
    total_count = len(magnets)

    return render_template(
        "index.html",
        magnets=display_magnets,
        magnet_count=total_count,
        display_count=len(display_magnets),
    )


@app.route("/magnets")
def magnets_view() -> str:
    """Magnets management view with search and pagination"""
    query = request.args.get("q", "").strip()
    try:
        page = int(request.args.get("page", 1))
        if page < 1:
            page = 1
    except ValueError:
        page = 1

    per_page = 50
    magnets, total_count = search_magnets(query=query, page=page, per_page=per_page)

    total_pages = math.ceil(total_count / per_page)

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
    """RSS 2.0 feed of magnet links"""
    magnets = read_magnets()

    # Get base URL - auto-detect from request or use env override
    base_url = os.getenv("BASE_URL")
    if not base_url:
        # Auto-detect from incoming request (works in Proxmox LXC, Docker, localhost)
        base_url = f"http://{request.host}"

    # Build RSS 2.0 XML
    rss_items = []
    for magnet in magnets:
        pub_date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
        guid = magnet["hash"]

        # Properly escape magnet link for XML (handles &, <, >, ", ')
        magnet_escaped = escape(magnet["magnet"])

        # Escape ]]> in CDATA content to prevent breaking CDATA block
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
        <title>{FEED_TITLE}</title>
        <link>{base_url}</link>
        <description>{FEED_DESCRIPTION}</description>
        <language>en-us</language>
        <lastBuildDate>{datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")}</lastBuildDate>
        <atom:link href="{base_url}/feed.xml" rel="self" type="application/rss+xml" />

        {"".join(rss_items)}
    </channel>
</rss>
"""

    return Response(rss_xml, mimetype="application/rss+xml")


@app.route("/health")
def health() -> dict[str, Any]:
    """Health check endpoint"""
    magnets = read_magnets()

    # Get list of magnet files for stats (sorted by date, newest first)
    magnet_files = sorted(glob.glob(os.path.join(MAGNETS_DIR, "magnets_*.txt")), reverse=True)

    # Safely get latest file (defensive against empty list)
    latest_file = None
    if magnet_files:
        latest_file = os.path.basename(magnet_files[0])

    return {
        "status": "ok",
        "magnet_count": len(magnets),
        "magnets_dir": MAGNETS_DIR,
        "magnet_files_count": len(magnet_files),
        "latest_file": latest_file,
    }


# Initialize config manager
config_manager = ConfigManager()


@app.route("/settings", methods=["GET", "POST"])
@requires_auth
def settings() -> str:
    """Settings page for BIND configuration"""
    message = None
    success = False

    if request.method == "POST":
        # Collect form data
        new_config = {
            "ABB_URL": request.form.get("ABB_URL", "").strip(),
            "SCRAPE_INTERVAL": request.form.get("SCRAPE_INTERVAL", "60").strip(),
            "BIND_PROXY": request.form.get("BIND_PROXY", "").strip(),
            "BASE_URL": request.form.get("BASE_URL", "").strip(),
            "CIRCUIT_BREAKER_THRESHOLD": request.form.get("CIRCUIT_BREAKER_THRESHOLD", "3").strip(),
            "CIRCUIT_BREAKER_COOLDOWN": request.form.get("CIRCUIT_BREAKER_COOLDOWN", "300").strip(),
        }

        # Save configuration
        write_success, write_message = config_manager.write_config(new_config)

        if write_success:
            # Attempt to restart daemon (may fail in dev mode, that's OK)
            restart_success, restart_message = config_manager.restart_daemon()
            if restart_success:
                message = "Configuration saved. Daemon restarted successfully."
                success = True
            else:
                message = f"Configuration saved. Note: {restart_message}"
                success = True  # Config was saved, just restart failed
        else:
            message = write_message
            success = False

    # Read current config for form
    config = config_manager.read_config()

    # Read current trackers
    trackers = tracker_manager.get_trackers()
    trackers_text = "\n".join(trackers)

    return render_template(
        "settings.html",
        config=config,
        trackers_text=trackers_text,
        message=message,
        success=success,
    )


@app.route("/settings/trackers", methods=["POST"])
@requires_auth
def settings_trackers() -> str:
    """Update tracker list from settings page."""
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
    """System logs view"""
    log_type = request.args.get("log", "security")

    # map log type to filename
    if log_type == "daemon":
        filename = "bind.log"
        # Assume bind.log is in the current working directory
        filepath = os.path.join(os.getcwd(), filename)
    elif log_type == "history":
        filename = "history.log"
        filepath = os.path.join(MAGNETS_DIR, filename)
    else:
        # Default to security
        log_type = "security"
        filename = "security.log"
        filepath = get_security_log_path()

    logs = []
    MAX_LINES = 1000

    if os.path.exists(filepath):
        try:
            with open(filepath, encoding="utf-8") as f:
                # Read all lines and take the last MAX_LINES
                lines = f.readlines()
                # Reverse to show newest first
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
    """First-time setup page for creating admin account."""
    # If setup is already complete, redirect to dashboard
    if is_setup_complete():
        return redirect("/")

    error = None
    username = ""

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Validate passwords match
        if password != confirm_password:
            error = "Passwords do not match."
        else:
            # Attempt to save credentials
            success, message = save_credentials(username, password)
            if success:
                return redirect("/")
            else:
                error = message

    return render_template("setup.html", error=error, username=username)


@app.route("/settings/password", methods=["POST"])
@requires_auth
def change_password_route() -> str:
    """Handle password change form submission."""
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

    # Re-render settings page with password message
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
    """
    Check if the BIND daemon is active by inspecting bind.log modification time.
    Returns (status_enum, status_message, last_active_ts)
    """
    try:
        # Default interval is 60 mins. We consider it stalled if > 2x interval.
        # Ideally we'd read this from config, but for now we'll assume standard behavior.
        # If we can read config, even better.
        config = config_manager.read_config()
        interval = int(config.get("SCRAPE_INTERVAL", 60))

        # Path to bind.log (assumed in CWD as per logs_view)
        log_path = os.path.join(os.getcwd(), "bind.log")

        if not os.path.exists(log_path):
            return "unknown", "Log file not found", 0

        mtime = os.path.getmtime(log_path)
        last_active = datetime.fromtimestamp(mtime, tz=timezone.utc)
        now = datetime.now(timezone.utc)

        diff_minutes = (now - last_active).total_seconds() / 60

        if diff_minutes < (interval * 2) + 5:  # Small buffer
            return "online", f"Active (Last job: {int(diff_minutes)}m ago)", mtime
        else:
            return "offline", f"Stalled (Last job: {int(diff_minutes)}m ago)", mtime

    except Exception as e:
        return "unknown", f"Error checking status: {str(e)}", 0


@app.route("/api/stats")
def api_stats() -> dict[str, Any]:
    """
    API Endpoint for real-time dashboard statistics.
    Returns JSON with system status and magnet counts.
    """
    status, message, _ = check_daemon_status()

    # Get magnet counts
    # Optimization: read_magnets reads all files.
    # For a simple count, we can just count lines in files if perf is an issue,
    # but read_magnets is safe for now (~1k items).
    magnets = read_magnets()
    count = len(magnets)

    # Get recent magnets for dashboard list (limit 5 for "Recent Index" widget, or 20 if we want to fill the page)
    # The dashboard currently shows 20, let's return 20 to match.
    recent_magnets = magnets[:20]

    return {
        "system_status": status,
        "status_message": message,
        "magnet_count": count,
        "recent_magnets": recent_magnets,
        "server_time": datetime.now(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z"),
    }


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5050))
    host = os.getenv("HOST", "0.0.0.0")

    print(f"Starting BIND RSS Server on {host}:{port}")
    print(f"RSS Feed: http://{host}:{port}/feed.xml")
    print(f"Web UI: http://{host}:{port}/")

    app.run(host=host, port=port, debug=False)
