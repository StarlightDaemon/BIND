"""
BIND Security Module
IP Allowlist, Basic Authentication, and First-Time Setup for Web UI protection.
Credentials storage with failed login protection and audit logging.
"""

import fcntl
import ipaddress
import json
import logging
import os
import re
import time
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, TypeVar, cast

from flask import Flask, Response, request
from werkzeug.security import check_password_hash, generate_password_hash

F = TypeVar("F", bound=Callable[..., Any])

# =============================================================================
# Constants
# =============================================================================

CREDENTIALS_VERSION = 2
PASSWORD_MIN_LENGTH = 8
PASSWORD_PATTERN = r"^(?=.*[0-9!@#$%^&*()\-_=+\[\]{}|;:,.<>?]).{8,}$"
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15
_IP_BLOCKED_LAST_LOG: dict[str, float] = {}  # IP → monotonic timestamp of last logged event
_IP_BLOCKED_RATE_LIMIT_SECS = 60.0

# Security logger
security_logger = logging.getLogger("BIND.security")


# =============================================================================
# File Paths
# =============================================================================


def get_base_dir() -> str:
    """Get BIND base directory."""
    if os.path.exists("/opt/bind"):
        return "/opt/bind"
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_data_dir() -> str:
    """Get writable data directory (credentials, database)."""
    path = os.path.join(get_base_dir(), "data")
    os.makedirs(path, exist_ok=True)
    return path


def get_logs_dir() -> str:
    """Get writable logs directory."""
    path = os.path.join(get_base_dir(), "logs")
    os.makedirs(path, exist_ok=True)
    return path


def get_credentials_path() -> str:
    """Get path to credentials.json file."""
    return os.path.join(get_data_dir(), "credentials.json")


def get_security_log_path() -> str:
    """Get path to security.log file."""
    return os.path.join(get_logs_dir(), "security.log")


CREDENTIALS_FILE = get_credentials_path()


# =============================================================================
# Audit Logging
# =============================================================================


def log_security_event(event_type: str, username: str, ip: str, details: str = "") -> None:
    """
    Log a security event to security.log.

    Event types: LOGIN_SUCCESS, LOGIN_FAILED, ACCOUNT_LOCKED, PASSWORD_CHANGED, ACCOUNT_CREATED,
                 CSRF_FAILED, IP_BLOCKED, SETUP_REJECTED, LOGOUT, ACCOUNT_UNLOCKED
    """
    timestamp = datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
    log_line = f"{timestamp} {event_type} {username} {ip}"
    if details:
        log_line += f" {details}"

    security_logger.info(log_line)

    # Also write to dedicated security log file
    try:
        log_path = get_security_log_path()
        with open(log_path, "a", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(log_line + "\n")
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

        # Rotate log if too large (keep last 1000 lines)
        _rotate_log_if_needed(log_path, max_lines=1000)
    except OSError:
        pass  # Don't fail on log write errors


def _rotate_log_if_needed(log_path: str, max_lines: int = 1000) -> None:
    """Rotate log file if it exceeds max_lines, holding an exclusive lock across read+write."""
    try:
        with open(log_path, "r+", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                lines = f.readlines()
                if len(lines) > max_lines:
                    f.seek(0)
                    f.writelines(lines[-max_lines:])
                    f.truncate()
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except OSError:
        pass


# =============================================================================
# Credentials Storage
# =============================================================================


def is_setup_complete() -> bool:
    """Check if first-time setup has been completed."""
    return os.path.exists(CREDENTIALS_FILE)


def load_credentials() -> dict[str, Any]:
    """Load credentials from JSON file with migration support."""
    if not is_setup_complete():
        return cast(dict[str, Any], {})

    try:
        with open(CREDENTIALS_FILE, encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            try:
                creds = json.load(f)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

        # Migrate v1 to v2 if needed
        if creds.get("version", 1) < CREDENTIALS_VERSION:
            creds = _migrate_credentials(creds)

        return cast(dict[str, Any], creds)
    except (OSError, json.JSONDecodeError):
        return cast(dict[str, Any], {})


def _migrate_credentials(creds: dict[str, Any]) -> dict[str, Any]:
    """Migrate credentials to latest version."""
    version = creds.get("version", 1)

    if version < 2:
        # Add v2 fields
        creds["version"] = 2
        creds.setdefault("updated_at", creds.get("created_at"))
        creds.setdefault("failed_attempts", 0)
        creds.setdefault("locked_until", None)
        creds.setdefault("last_login", None)
        creds.setdefault("last_login_ip", None)

        # Save migrated credentials
        _save_credentials_raw(creds)

    return creds


def _save_credentials_raw(creds: dict[str, Any]) -> bool:
    """Save credentials dict directly to file."""
    try:
        with open(CREDENTIALS_FILE, "w", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                json.dump(creds, f, indent=2)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        os.chmod(CREDENTIALS_FILE, 0o600)
        return True
    except OSError:
        return False


def validate_password(password: str) -> tuple[bool, str]:
    """
    Validate password meets security requirements.

    Returns:
        Tuple of (is_valid: bool, error_message: str)
    """
    if len(password) < PASSWORD_MIN_LENGTH:
        return False, f"Password must be at least {PASSWORD_MIN_LENGTH} characters."

    if not re.match(PASSWORD_PATTERN, password):
        return False, "Password must contain at least one number or special character."

    return True, ""


def save_credentials(username: str, password: str, ip: str = "") -> tuple[bool, str]:
    """
    Save new credentials to JSON file (first-time setup).

    Args:
        username: Admin username
        password: Plain text password (will be hashed)
        ip: Client IP for audit log (caller's responsibility to resolve)

    Returns:
        Tuple of (success: bool, message: str)
    """
    # Validate username
    if not re.match(r"^[a-zA-Z0-9_]{3,32}$", username):
        return False, "Username must be 3-32 characters, alphanumeric or underscore."

    # Validate password
    is_valid, error = validate_password(password)
    if not is_valid:
        return False, error

    now = datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")

    credentials = {
        "version": CREDENTIALS_VERSION,
        "username": username,
        "password_hash": generate_password_hash(password),
        "created_at": now,
        "updated_at": now,
        "failed_attempts": 0,
        "locked_until": None,
        "last_login": None,
        "last_login_ip": None,
    }

    if _save_credentials_raw(credentials):
        log_security_event("ACCOUNT_CREATED", username, ip)
        return True, "Account created successfully."
    else:
        return False, "Failed to save credentials."


def change_password(current_password: str, new_password: str, ip: str = "") -> tuple[bool, str]:
    """
    Change the admin password.

    Args:
        current_password: Current plain text password for verification
        new_password: New plain text password
        ip: Client IP for audit log (caller's responsibility to resolve)

    Returns:
        Tuple of (success: bool, message: str)
    """
    creds = load_credentials()

    if not creds:
        return False, "No credentials found."

    # Verify current password
    if not check_password_hash(creds.get("password_hash", ""), current_password):
        log_security_event(
            "PASSWORD_CHANGE_FAILED",
            creds.get("username", "unknown"),
            ip,
            "invalid_current_password",
        )
        return False, "Current password is incorrect."

    # Validate new password
    is_valid, error = validate_password(new_password)
    if not is_valid:
        return False, error

    # Update password
    creds["password_hash"] = generate_password_hash(new_password)
    creds["updated_at"] = (
        datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
    )

    if _save_credentials_raw(creds):
        log_security_event("PASSWORD_CHANGED", creds.get("username", "unknown"), ip)
        return True, "Password changed successfully."
    else:
        return False, "Failed to save new password."


def is_account_locked() -> tuple[bool, int | None]:
    """
    Check if account is currently locked.

    Returns:
        Tuple of (is_locked: bool, minutes_remaining: Optional[int])
    """
    creds = load_credentials()

    locked_until = creds.get("locked_until")
    if not locked_until:
        return False, None

    try:
        locked_time = datetime.fromisoformat(locked_until.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)

        if now < locked_time:
            remaining = (locked_time - now).total_seconds() / 60
            return True, int(remaining) + 1
        else:
            # Lockout expired, clear it
            creds["locked_until"] = None
            creds["failed_attempts"] = 0
            _save_credentials_raw(creds)
            try:
                client_ip = get_client_ip(request)
            except RuntimeError:
                client_ip = "0.0.0.0"
            log_security_event(
                "ACCOUNT_UNLOCKED",
                creds.get("username", "unknown"),
                client_ip,
            )
            return False, None
    except (ValueError, TypeError):
        return False, None


def record_failed_login(ip: str) -> None:
    """Record a failed login attempt and lock account if threshold exceeded."""
    creds = load_credentials()
    if not creds:
        return

    creds["failed_attempts"] = creds.get("failed_attempts", 0) + 1

    log_security_event(
        "LOGIN_FAILED", creds.get("username", "unknown"), ip, f"attempt={creds['failed_attempts']}"
    )

    if creds["failed_attempts"] >= MAX_FAILED_ATTEMPTS:
        # Lock account
        lock_time = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        creds["locked_until"] = lock_time.isoformat(timespec="microseconds").replace("+00:00", "Z")
        log_security_event(
            "ACCOUNT_LOCKED",
            creds.get("username", "unknown"),
            ip,
            f"duration={LOCKOUT_DURATION_MINUTES}min",
        )

    _save_credentials_raw(creds)


def record_successful_login(ip: str) -> None:
    """Record a successful login attempt."""
    creds = load_credentials()
    if not creds:
        return

    # Clear failed attempts
    creds["failed_attempts"] = 0
    creds["locked_until"] = None
    creds["last_login"] = (
        datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
    )
    creds["last_login_ip"] = ip

    log_security_event("LOGIN_SUCCESS", creds.get("username", "unknown"), ip)

    _save_credentials_raw(creds)


def verify_credentials(username: str, password: str, ip: str = "") -> bool:
    """Verify username and password against stored credentials."""
    creds = load_credentials()

    if not creds:
        return False

    # Check if locked
    is_locked, minutes = is_account_locked()
    if is_locked:
        return False

    if creds.get("username") != username:
        record_failed_login(ip)
        return False

    if check_password_hash(creds.get("password_hash", ""), password):
        record_successful_login(ip)
        return True
    else:
        record_failed_login(ip)
        return False


# =============================================================================
# IP Allowlist
# =============================================================================

DEFAULT_ALLOWED_NETWORKS = [
    "127.0.0.0/8",  # Localhost
    "10.0.0.0/8",  # Class A private
    "172.16.0.0/12",  # Class B private
    "192.168.0.0/16",  # Class C private
]


def get_allowed_networks() -> list[str]:
    """
    Get list of allowed IP networks from environment or defaults.

    Environment variable BIND_ALLOWED_IPS accepts comma-separated CIDR notation.
    Example: "192.168.1.0/24,10.0.0.0/8"
    """
    env_networks = os.getenv("BIND_ALLOWED_IPS", "")

    if env_networks:
        return [n.strip() for n in env_networks.split(",") if n.strip()]

    return DEFAULT_ALLOWED_NETWORKS


def is_ip_allowed(ip_str: str) -> bool:
    """
    Check if an IP address is in the allowed networks.

    Args:
        ip_str: IP address as string (e.g., "192.168.1.100")

    Returns:
        True if IP is in an allowed network, False otherwise.
    """
    try:
        client_ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False

    for network_str in get_allowed_networks():
        try:
            network = ipaddress.ip_network(network_str, strict=False)
            if client_ip in network:
                return True
        except ValueError:
            continue

    return False


DEFAULT_TRUSTED_PROXIES = "127.0.0.1/32,::1/128"

# Module-level parse cache for BIND_TRUSTED_PROXIES. Parsing CIDRs on every
# request is wasteful, but the env var can change between requests (tests,
# config reloads), so the cache is keyed on the raw string and invalidated
# whenever that string changes.
_TRUSTED_PROXY_CACHE_KEY: str | None = None
_TRUSTED_PROXY_NETS: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []


def get_trusted_proxy_networks() -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    """
    Parse the trusted-proxy CIDR set from the environment.

    Read from BIND_TRUSTED_PROXIES (comma-separated CIDRs) at request time,
    mirroring how BIND_ALLOWED_IPS is read. Default
    "127.0.0.1/32,::1/128" exactly preserves the historical loopback-only
    trust behaviour when the variable is unset. Unparseable entries are
    skipped. Results are cached per raw value to avoid re-parsing on every
    request.
    """
    global _TRUSTED_PROXY_CACHE_KEY, _TRUSTED_PROXY_NETS

    raw = os.getenv("BIND_TRUSTED_PROXIES", "") or DEFAULT_TRUSTED_PROXIES
    if raw == _TRUSTED_PROXY_CACHE_KEY:
        return _TRUSTED_PROXY_NETS

    nets: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        try:
            nets.append(ipaddress.ip_network(entry, strict=False))
        except ValueError:
            continue

    _TRUSTED_PROXY_CACHE_KEY = raw
    _TRUSTED_PROXY_NETS = nets
    return nets


def _is_trusted_proxy(ip_str: str) -> bool:
    """Return True if ip_str parses and falls inside the trusted-proxy set."""
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return any(ip in net for net in get_trusted_proxy_networks())


def get_client_ip(req: Any) -> str:
    """
    Extract the real client IP using rightmost-untrusted XFF parsing.

    The direct TCP peer (``req.remote_addr``) is checked against the
    configurable trusted-proxy set (``BIND_TRUSTED_PROXIES``):

    - If the peer is NOT trusted, it is the client and is returned verbatim;
      X-Forwarded-For is ignored (an untrusted peer can forge it).
    - If the peer IS trusted, the chain ``[XFF entries..., peer]`` is walked
      from the right, skipping every address inside the trusted set. The
      first untrusted address encountered is the real client.
    - If the entire chain is trusted (or XFF is empty), the leftmost XFF
      entry is returned if present, else the peer.

    Malformed XFF entries: if an unparseable token is reached during the
    right-to-left walk, the walk stops and that token is returned verbatim.
    This is safe because ``is_ip_allowed`` returns False for any unparseable
    input, so the request is denied (fail-closed) and the audit log records
    exactly what the upstream sent rather than silently skipping it (which
    could let a forged entry hide behind a malformed one).
    """
    if req is None:
        return "0.0.0.0"

    peer = (req.remote_addr or "0.0.0.0").strip()
    try:
        ipaddress.ip_address(peer)
    except ValueError:
        return "0.0.0.0"

    # Untrusted direct peer: it is the client; never trust its XFF.
    if not _is_trusted_proxy(peer):
        return peer

    forwarded = req.headers.get("X-Forwarded-For", "") or ""
    xff_entries = [e.strip() for e in forwarded.split(",") if e.strip()]

    # Chain is [client, ...proxies, peer]; peer is appended as the final hop.
    chain = xff_entries + [peer]

    # Walk from the right, skipping trusted hops.
    for hop in reversed(chain):
        if _is_trusted_proxy(hop):
            continue
        # First untrusted hop (or a malformed/unparseable token) — return it
        # verbatim. is_ip_allowed denies unparseable input, so this is safe.
        return hop

    # Entire chain trusted: prefer the leftmost XFF entry, else the peer.
    if xff_entries:
        return xff_entries[0]
    return peer


def ip_allowlist_middleware(app: Flask) -> None:
    """
    Register IP allowlist check as Flask before_request handler.

    If BIND_IP_FILTER is set to 'false', filtering is disabled.
    """

    @app.before_request
    def check_ip_allowlist() -> Response | None:
        if os.getenv("BIND_IP_FILTER", "true").lower() == "false":
            return None

        client_ip = get_client_ip(request)

        if not is_ip_allowed(client_ip):
            now = time.monotonic()
            last = _IP_BLOCKED_LAST_LOG.get(client_ip, 0.0)
            if now - last >= _IP_BLOCKED_RATE_LIMIT_SECS:
                _IP_BLOCKED_LAST_LOG[client_ip] = now
                log_security_event("IP_BLOCKED", "-", client_ip, f"path={request.path}")
            return Response(
                f"Access denied. Your IP ({client_ip}) is not in the allowlist.",
                status=403,
                mimetype="text/plain",
            )

        return None


# =============================================================================
# Authentication
# =============================================================================


def check_auth(username: str, password: str) -> bool:
    """
    Validate username and password.

    Uses stored credentials if setup is complete. Fails closed if
    first-time setup has not been completed.
    """
    client_ip = get_client_ip(request)

    # If setup is complete, use stored credentials (verify_credentials checks lock internally)
    if is_setup_complete():
        return verify_credentials(username, password, client_ip)

    return False  # setup not complete — fail closed


def requires_auth(f: F) -> F:
    """
    Decorator to require Basic Authentication on a route.

    If BIND_AUTH_ENABLED is 'false', auth is skipped.

    Usage:
        @app.route('/settings')
        @requires_auth
        def settings():
            ...
    """

    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        if os.getenv("BIND_AUTH_ENABLED", "true").lower() == "false":
            return f(*args, **kwargs)

        # Check if locked
        is_locked, minutes = is_account_locked()
        if is_locked:
            return Response(
                f"Account locked. Try again in {minutes} minutes.",
                status=403,
                mimetype="text/plain",
            )

        auth = request.authorization

        if (
            not auth
            or not auth.username
            or not auth.password
            or not check_auth(auth.username, auth.password)
        ):
            return Response(
                "Authentication required.",
                status=401,
                headers={"WWW-Authenticate": 'Basic realm="BIND Settings"'},
            )

        return f(*args, **kwargs)

    return cast(F, decorated)
