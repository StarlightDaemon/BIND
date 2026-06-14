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

from src.config_manager import LiveConfig

F = TypeVar("F", bound=Callable[..., Any])

# Live view of config.env (SEC-2). security.py must not import rss_server, so
# it owns its own instance; both read the same file. BIND_IP_FILTER and
# BIND_AUTH_ENABLED are read through it per request.
live_config = LiveConfig()

# =============================================================================
# Constants
# =============================================================================

CREDENTIALS_VERSION = 3
PASSWORD_MIN_LENGTH = 8
PASSWORD_PATTERN = r"^(?=.*[0-9!@#$%^&*()\-_=+\[\]{}|;:,.<>?]).{8,}$"
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15
# A distributed attack spread across many source IPs would never trip any single
# per-IP counter. The global counter is kept as a ceiling: once total failures
# across all IPs reach this many, the account locks globally regardless of source.
GLOBAL_LOCKOUT_MULTIPLIER = 5
GLOBAL_MAX_FAILED_ATTEMPTS = MAX_FAILED_ATTEMPTS * GLOBAL_LOCKOUT_MULTIPLIER  # 25
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
    """
    Migrate credentials to the latest schema version.

    Migration is incremental (v1 → v2 → v3) and idempotent: every step uses
    ``setdefault`` so existing fields — including an active ``locked_until`` /
    ``failed_attempts`` lockout — are preserved untouched.
    """
    version = creds.get("version", 1)
    dirty = False

    if version < 2:
        # Add v2 fields
        creds["version"] = 2
        version = 2
        creds.setdefault("updated_at", creds.get("created_at"))
        creds.setdefault("failed_attempts", 0)
        creds.setdefault("locked_until", None)
        creds.setdefault("last_login", None)
        creds.setdefault("last_login_ip", None)
        dirty = True

    if version < 3:
        # v3 adds per-IP failure tracking. The existing global failed_attempts /
        # locked_until are deliberately left as-is (they remain the global
        # ceiling), so an account that is currently locked stays locked.
        creds["version"] = 3
        version = 3
        creds.setdefault("failed_by_ip", {})
        dirty = True

    if dirty:
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


def _locked_update(mutator: Callable[[dict[str, Any]], dict[str, Any]]) -> bool:
    """
    Apply ``mutator`` to the credentials file under a single exclusive lock held
    across the full read-modify-write cycle.

    Opens the file ``r+``, takes ``fcntl.LOCK_EX``, loads the current JSON,
    runs the (possibly migrating) mutator, then ``seek(0)`` / write / ``truncate``
    while still holding the lock. This closes the lost-update race between
    concurrent gunicorn workers, where locks previously covered only the
    individual read and write.

    Returns False (without raising) if the file is missing or unreadable, so
    callers keep their historical "no creds → silent no-op" behaviour.
    """
    try:
        with open(CREDENTIALS_FILE, "r+", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                try:
                    creds = json.load(f)
                except json.JSONDecodeError:
                    return False

                # Migrate in-place under the lock so a v1/v2 file gains the v3
                # fields before mutation, without a second unlocked write.
                if creds.get("version", 1) < CREDENTIALS_VERSION:
                    creds = _migrate_in_place(creds)

                creds = mutator(creds)

                f.seek(0)
                json.dump(creds, f, indent=2)
                f.truncate()
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        os.chmod(CREDENTIALS_FILE, 0o600)
        return True
    except OSError:
        return False


def _migrate_in_place(creds: dict[str, Any]) -> dict[str, Any]:
    """
    Schema upgrade used inside _locked_update — same field additions as
    _migrate_credentials but WITHOUT writing (the caller already holds the lock
    and will persist). Idempotent and lockout-preserving.
    """
    version = creds.get("version", 1)
    if version < 2:
        creds["version"] = 2
        version = 2
        creds.setdefault("updated_at", creds.get("created_at"))
        creds.setdefault("failed_attempts", 0)
        creds.setdefault("locked_until", None)
        creds.setdefault("last_login", None)
        creds.setdefault("last_login_ip", None)
    if version < 3:
        creds["version"] = 3
        creds.setdefault("failed_by_ip", {})
    return creds


def _now_iso() -> str:
    """Return the current UTC time as a 'Z'-suffixed ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _is_locked_until(locked_until: Any) -> bool:
    """True if the given ISO timestamp is a still-active lockout (future)."""
    if not locked_until:
        return False
    try:
        locked_time = datetime.fromisoformat(str(locked_until).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return False
    return datetime.now(timezone.utc) < locked_time


def _prune_ip_entries(failed_by_ip: dict[str, Any]) -> dict[str, Any]:
    """
    Drop per-IP entries that are both expired (no active lockout) and have a
    zero count, so the file does not grow unboundedly. Kept entries are those
    still counting toward a lockout or currently locked.
    """
    pruned: dict[str, Any] = {}
    for ip, entry in failed_by_ip.items():
        if not isinstance(entry, dict):
            continue
        count = int(entry.get("count", 0) or 0)
        if count > 0 or _is_locked_until(entry.get("locked_until")):
            pruned[ip] = entry
    return pruned


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
        "failed_by_ip": {},
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


def _minutes_remaining(locked_until: Any) -> int:
    """Whole minutes (rounded up, min 1) until the given ISO lockout expires."""
    locked_time = datetime.fromisoformat(str(locked_until).replace("Z", "+00:00"))
    remaining = (locked_time - datetime.now(timezone.utc)).total_seconds() / 60
    return int(remaining) + 1


def is_account_locked(ip: str | None = None) -> tuple[bool, int | None]:
    """
    Check whether authentication is currently locked.

    Two layers are evaluated:
      1. Global ceiling (``locked_until`` / ``failed_attempts``): trips only at
         GLOBAL_MAX_FAILED_ATTEMPTS total failures across all source IPs, so a
         distributed attack is still stopped while a single misbehaving IP can
         no longer DoS the only account.
      2. Per-IP lockout (``failed_by_ip[ip]``): today's semantics (5 failures →
         15 min) scoped to the requesting source IP.

    When ``ip`` is None only the global ceiling is checked (used by callers that
    have no request context).

    Expired lockouts are cleared in place under an exclusive lock; clearing the
    global lockout emits ACCOUNT_UNLOCKED exactly as before.

    Returns:
        Tuple of (is_locked: bool, minutes_remaining: Optional[int])
    """
    creds = load_credentials()
    if not creds:
        return False, None

    # --- Global ceiling -----------------------------------------------------
    global_locked_until = creds.get("locked_until")
    if global_locked_until:
        if _is_locked_until(global_locked_until):
            return True, _minutes_remaining(global_locked_until)

        # Global lockout expired — clear it (and reset the global counter) under
        # the lock, preserving the ACCOUNT_UNLOCKED audit event.
        def _clear_global(c: dict[str, Any]) -> dict[str, Any]:
            c["locked_until"] = None
            c["failed_attempts"] = 0
            return c

        if _locked_update(_clear_global):
            try:
                client_ip = get_client_ip(request)
            except RuntimeError:
                client_ip = "0.0.0.0"
            log_security_event(
                "ACCOUNT_UNLOCKED",
                creds.get("username", "unknown"),
                client_ip,
            )

    # --- Per-IP lockout -----------------------------------------------------
    if ip:
        entry = creds.get("failed_by_ip", {}).get(ip)
        if entry and _is_locked_until(entry.get("locked_until")):
            return True, _minutes_remaining(entry["locked_until"])

    return False, None


def record_failed_login(ip: str) -> None:
    """
    Record a failed login attempt.

    Increments both the per-IP counter (locking that IP at MAX_FAILED_ATTEMPTS)
    and the global counter (locking the whole account at the
    GLOBAL_MAX_FAILED_ATTEMPTS ceiling). The full read-modify-write runs under a
    single exclusive lock so concurrent workers cannot lose an increment.

    Audit events (LOGIN_FAILED, ACCOUNT_LOCKED) are emitted after the locked
    write using the values captured during mutation.
    """
    events: dict[str, Any] = {}

    def _mutate(creds: dict[str, Any]) -> dict[str, Any]:
        # Global counter
        creds["failed_attempts"] = int(creds.get("failed_attempts", 0)) + 1
        events["global_attempts"] = creds["failed_attempts"]
        events["username"] = creds.get("username", "unknown")

        # Per-IP counter
        failed_by_ip = creds.get("failed_by_ip", {})
        if not isinstance(failed_by_ip, dict):
            failed_by_ip = {}
        entry = failed_by_ip.get(ip) or {"count": 0, "locked_until": None}
        entry["count"] = int(entry.get("count", 0)) + 1
        events["ip_attempts"] = entry["count"]

        # Per-IP lockout
        if entry["count"] >= MAX_FAILED_ATTEMPTS:
            lock_time = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
            entry["locked_until"] = lock_time.isoformat(timespec="microseconds").replace(
                "+00:00", "Z"
            )
            events["ip_locked"] = True
        failed_by_ip[ip] = entry

        # Prune stale entries (expired + zero count); the active entry survives.
        creds["failed_by_ip"] = _prune_ip_entries(failed_by_ip)

        # Global ceiling lockout
        if creds["failed_attempts"] >= GLOBAL_MAX_FAILED_ATTEMPTS:
            lock_time = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
            creds["locked_until"] = lock_time.isoformat(timespec="microseconds").replace(
                "+00:00", "Z"
            )
            events["global_locked"] = True
        return creds

    if not _locked_update(_mutate):
        return

    username = events.get("username", "unknown")
    log_security_event("LOGIN_FAILED", username, ip, f"attempt={events.get('ip_attempts')}")
    if events.get("ip_locked"):
        log_security_event(
            "ACCOUNT_LOCKED",
            username,
            ip,
            f"scope=ip duration={LOCKOUT_DURATION_MINUTES}min",
        )
    if events.get("global_locked"):
        log_security_event(
            "ACCOUNT_LOCKED",
            username,
            ip,
            f"scope=global duration={LOCKOUT_DURATION_MINUTES}min",
        )


def record_successful_login(ip: str) -> None:
    """
    Record a successful login.

    A successful auth proves the credential, so this clears the global counter
    and lockout and removes this IP's failure entry. Other IPs' counters are
    intentionally left intact (a successful login from one source does not prove
    that concurrent attempts from a different source are benign). The full
    read-modify-write runs under a single exclusive lock.
    """
    events: dict[str, Any] = {}

    def _mutate(creds: dict[str, Any]) -> dict[str, Any]:
        events["username"] = creds.get("username", "unknown")
        creds["failed_attempts"] = 0
        creds["locked_until"] = None
        failed_by_ip = creds.get("failed_by_ip", {})
        if isinstance(failed_by_ip, dict):
            failed_by_ip.pop(ip, None)
            creds["failed_by_ip"] = _prune_ip_entries(failed_by_ip)
        else:
            creds["failed_by_ip"] = {}
        creds["last_login"] = _now_iso()
        creds["last_login_ip"] = ip
        return creds

    if not _locked_update(_mutate):
        return

    log_security_event("LOGIN_SUCCESS", events.get("username", "unknown"), ip)


def verify_credentials(username: str, password: str, ip: str = "") -> bool:
    """Verify username and password against stored credentials."""
    creds = load_credentials()

    if not creds:
        return False

    # Check if locked (per-IP + global ceiling)
    is_locked, minutes = is_account_locked(ip=ip or None)
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


def ip_allowlist_middleware(app: Flask, config: LiveConfig | None = None) -> None:
    """
    Register IP allowlist check as Flask before_request handler.

    BIND_IP_FILTER is read live per request (SEC-2): setting it to 'false'
    via the Settings UI disables filtering within seconds, no restart.

    Args:
        app: Flask app to register the handler on.
        config: LiveConfig to read flags through; the caller may inject its
            own instance (rss_server does). Defaults to this module's.
    """
    cfg = config if config is not None else live_config

    @app.before_request
    def check_ip_allowlist() -> Response | None:
        if not cfg.get_bool("BIND_IP_FILTER"):
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
        # Read live per request (SEC-2): applies within seconds of a change.
        if not live_config.get_bool("BIND_AUTH_ENABLED"):
            return f(*args, **kwargs)

        # Check if locked (per-IP for this client + global ceiling)
        is_locked, minutes = is_account_locked(ip=get_client_ip(request))
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
