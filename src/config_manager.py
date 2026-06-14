"""
BIND Configuration Manager
Handles reading/writing config.env and daemon restart.
"""

import fcntl
import ipaddress
import logging
import os
import re
import subprocess
import tempfile
import threading
from typing import Any

logger = logging.getLogger("ConfigManager")


class ConfigManager:
    """Manages BIND configuration via config.env file."""

    # Default configuration values
    DEFAULTS = {
        "ABB_URL": "http://audiobookbay.lu",
        "SCRAPE_INTERVAL": "60",
        "BIND_PROXY": "",
        "BASE_URL": "",
        "CIRCUIT_BREAKER_THRESHOLD": "3",
        "CIRCUIT_BREAKER_COOLDOWN": "300",
        "BIND_DB_PATH": "data/bind.db",
        "BIND_PROXIES": "",
        "BIND_JOB_TIMEOUT": "3600",
        "BIND_IP_FILTER": "true",
        "BIND_AUTH_ENABLED": "true",
        "SCRAPING_ENABLED": "true",
        "BIND_COOKIE_SECURE": "false",
    }

    # Validation rules: (min, max) for integers, 'url' for URLs, 'proxy' for proxy URLs
    VALIDATORS = {
        "ABB_URL": "url",
        "SCRAPE_INTERVAL": (15, 1440),
        "BIND_PROXY": "proxy",
        "BASE_URL": "url_optional",
        "CIRCUIT_BREAKER_THRESHOLD": (1, 10),
        "CIRCUIT_BREAKER_COOLDOWN": (60, 3600),
        "BIND_PROXIES": "proxy_list",
        "BIND_JOB_TIMEOUT": (60, 86400),
        "BIND_IP_FILTER": "boolean",
        "BIND_AUTH_ENABLED": "boolean",
        "SCRAPING_ENABLED": "boolean",
        "BIND_COOKIE_SECURE": "boolean",
    }

    def __init__(self, config_path: str | None = None):
        """
        Initialize ConfigManager.

        Args:
            config_path: Path to config.env file. Defaults to /opt/bind/config.env
                         or ./config.env if running locally.
        """
        if config_path:
            self.config_path = config_path
        elif os.path.exists("/opt/bind/config.env"):
            self.config_path = "/opt/bind/config.env"
        elif os.environ.get("BIND_DB_PATH"):
            # Docker: derive config dir from the DB path (e.g. /app/data/bind.db → /app/data/config.env)
            data_dir = os.path.dirname(os.environ["BIND_DB_PATH"])
            self.config_path = os.path.join(data_dir, "config.env")
        else:
            # Local development fallback
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.config_path = os.path.join(base_dir, "config.env")

    def read_config(self) -> dict[str, str]:
        """
        Read configuration from config.env file.

        Returns:
            Dict of configuration values with defaults for missing keys.
        """
        config = self.DEFAULTS.copy()

        if not os.path.exists(self.config_path):
            return config

        try:
            with open(self.config_path, encoding="utf-8") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    for line in f:
                        line = line.strip()
                        # Skip comments and empty lines
                        if not line or line.startswith("#"):
                            continue
                        # Parse KEY=VALUE
                        if "=" in line:
                            key, value = line.split("=", 1)
                            key = key.strip()
                            value = value.strip()
                            if key in self.DEFAULTS:
                                config[key] = value
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except OSError as e:
            print(f"Warning: Could not read config file: {e}")

        return config

    def write_config(self, settings: dict[str, str]) -> tuple[bool, str]:
        """
        Write configuration to config.env file.

        Args:
            settings: Dict of configuration values to save.

        Returns:
            Tuple of (success: bool, message: str)
        """
        # Validate all settings first
        for key, value in settings.items():
            if key in self.VALIDATORS:
                is_valid, error = self._validate(key, value)
                if not is_valid:
                    return False, error

        # Collect any admin-managed keys that exist in the file but are not in DEFAULTS
        preserved: dict[str, str] = {}
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            if k not in self.DEFAULTS:
                                preserved[k] = v.strip()
            except OSError:
                pass

        # Build config file content
        lines = [
            "# BIND Configuration",
            "# Generated by Web UI - Edit via http://YOUR-IP:5050/settings",
            "# Or edit manually and restart: systemctl restart bind",
            "",
        ]

        for key in self.DEFAULTS:
            value = settings.get(key, self.DEFAULTS[key])
            lines.append(f"{key}={value}")

        if preserved:
            lines.append("")
            lines.append("# Admin-managed settings (not editable via UI)")
            for key, value in preserved.items():
                lines.append(f"{key}={value}")

        content = "\n".join(lines) + "\n"

        config_dir = os.path.dirname(self.config_path) or "."
        tmp_path: str | None = None
        try:
            fd, tmp_path = tempfile.mkstemp(dir=config_dir, prefix=".config_tmp_")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(content)
                    f.flush()
                    os.fsync(f.fileno())
            except Exception:
                os.close(fd)
                raise
            os.replace(tmp_path, self.config_path)
            tmp_path = None  # replacement succeeded; no cleanup needed
            return True, "Configuration saved successfully."
        except OSError as e:
            return False, f"Failed to write config: {e}"
        finally:
            if tmp_path is not None:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    def _validate(self, key: str, value: str) -> tuple[bool, str]:
        """
        Validate a configuration value.

        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        validator = self.VALIDATORS.get(key)

        if validator is None:
            return True, ""

        # Integer range validation
        if isinstance(validator, tuple):
            min_val, max_val = validator
            try:
                int_val = int(value)
                if int_val < min_val or int_val > max_val:
                    return False, f"{key} must be between {min_val} and {max_val}."
            except ValueError:
                return False, f"{key} must be a valid integer."
            return True, ""

        # URL validation
        if validator == "url":
            if not value:
                return False, f"{key} cannot be empty."
            if not re.match(r"^https?://", value):
                return False, f"{key} must be a valid HTTP/HTTPS URL."
            return True, ""

        # Optional URL validation
        if validator == "url_optional":
            if value and not re.match(r"^https?://", value):
                return False, f"{key} must be a valid HTTP/HTTPS URL or empty."
            return True, ""

        # Proxy validation (http, https, socks4, socks5)
        if validator == "proxy":
            if value and not re.match(r"^(https?|socks[45])://", value):
                return (
                    False,
                    f"{key} must be a valid proxy URL (http/https/socks4/socks5) or empty.",
                )
            return True, ""

        if validator == "boolean":
            if value.lower() not in ("true", "false"):
                return False, f"{key} must be 'true' or 'false'."
            return True, ""

        if validator == "proxy_list":
            if not value:
                return True, ""
            for entry in value.split(","):
                entry = entry.strip()
                if entry and not re.match(r"^(https?|socks[45])://", entry):
                    return (
                        False,
                        f"{key}: '{entry}' is not a valid proxy URL (http/https/socks4/socks5).",
                    )
            return True, ""

        if validator == "cidr_list":
            if not value:
                return True, ""
            for entry in value.split(","):
                entry = entry.strip()
                if not entry:
                    continue
                try:
                    ipaddress.ip_network(entry, strict=False)
                except ValueError:
                    return (
                        False,
                        f"{key}: '{entry}' is not a valid CIDR/IP network.",
                    )
            return True, ""

        return True, ""

    def restart_daemon(self) -> tuple[bool, str]:
        """
        Restart the BIND daemon via systemctl.

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Reload systemd to pick up any service file changes
            subprocess.run(
                ["systemctl", "daemon-reload"], capture_output=True, timeout=10, check=False
            )

            # Restart the BIND service
            subprocess.run(
                ["systemctl", "restart", "bind.service"],
                capture_output=True,
                timeout=30,
                check=True,
            )
            return True, "Daemon restarted successfully."
        except subprocess.TimeoutExpired:
            return False, "Daemon restart timed out."
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode("utf-8", errors="replace") if e.stderr else ""
            return False, f"Failed to restart daemon: {stderr}"
        except FileNotFoundError:
            return False, "systemctl not found. Running in development mode?"


# Sentinel distinguishing "never parsed" from "file missing" in LiveConfig.
_UNREAD = object()


class LiveConfig:
    """Live, cached view of ``config.env`` with process-environment precedence.

    Single source of truth for the managed keys (those in
    ``ConfigManager.DEFAULTS``). Effective precedence, highest first:

    1. **Process-start environment** — managed keys present in ``os.environ``
       when this instance is constructed are snapshotted (key *and* value) and
       win permanently. This preserves the operator contract: a variable
       exported via Docker ``environment:`` or a systemd ``Environment=`` line
       is pinned for the life of the process and cannot be overridden from the
       Settings UI.
    2. **config.env** — re-parsed only when the file's ``(mtime_ns, size)``
       signature changes; the file is stat'd on every call (one syscall).
    3. **``ConfigManager.DEFAULTS``**.

    There is deliberately *no* fallback to ``os.environ`` at call time:
    ``src/bind.py`` and ``src/rss_server.py`` no longer seed config.env into
    ``os.environ``, and values that merely originated from the config file
    must not shadow later file edits (SEC-2 / ARCH-2).
    """

    def __init__(self, config_path: str | None = None, env: dict[str, str] | None = None):
        """
        Args:
            config_path: Path to config.env (defaults to ConfigManager's
                resolution). Tests inject a ``tmp_path`` location here.
            env: Environment mapping to snapshot instead of ``os.environ``
                (tests inject ``{}`` to simulate "no operator-pinned vars").
        """
        self._manager = ConfigManager(config_path)
        source: dict[str, str] = dict(os.environ) if env is None else env
        # Public on purpose: tests may monkeypatch.setitem()/delitem() entries
        # to simulate operator-pinned environment variables.
        self.env_snapshot: dict[str, str] = {
            key: source[key] for key in ConfigManager.DEFAULTS if key in source
        }
        self._lock = threading.Lock()
        self._cache_sig: Any = _UNREAD
        self._cache: dict[str, str] = dict(ConfigManager.DEFAULTS)

    @property
    def config_path(self) -> str:
        return self._manager.config_path

    def get(self, key: str) -> str:
        """Return the effective value for a managed key (see class docstring)."""
        if key in self.env_snapshot:
            return self.env_snapshot[key]
        return self._file_config().get(key, ConfigManager.DEFAULTS.get(key, ""))

    def get_bool(self, key: str) -> bool:
        """True unless the effective value is the string ``"false"``.

        Matches the historical ``os.getenv(key, "true").lower() != "false"``
        semantics of SCRAPING_ENABLED / BIND_AUTH_ENABLED / BIND_IP_FILTER.
        """
        return self.get(key).strip().lower() != "false"

    def get_int(self, key: str) -> int:
        """Effective value as int, falling back to the default on garbage."""
        try:
            return int(self.get(key))
        except (TypeError, ValueError):
            default = ConfigManager.DEFAULTS[key]
            logger.warning("Invalid integer for %s — using default %s", key, default)
            return int(default)

    def _file_config(self) -> dict[str, str]:
        """Parsed config.env merged over DEFAULTS, re-read on file change."""
        try:
            st = os.stat(self._manager.config_path)
            sig: Any = (st.st_mtime_ns, st.st_size)
        except OSError:
            sig = None
        with self._lock:
            if sig != self._cache_sig:
                self._cache = self._manager.read_config()
                self._cache_sig = sig
            return self._cache
