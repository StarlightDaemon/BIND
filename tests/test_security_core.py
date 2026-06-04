"""
Pure-utility branch tests for src/security.py.

All tests here avoid Flask request context. The autouse `isolated_credentials`
fixture redirects CREDENTIALS_FILE to a temp path so no real credentials.json
is touched.
"""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def isolated_credentials(tmp_path, monkeypatch):
    cred_path = str(tmp_path / "credentials.json")
    monkeypatch.setattr("src.security.CREDENTIALS_FILE", cred_path)
    return cred_path


# ---------------------------------------------------------------------------
# 1. get_base_dir() — /opt/bind branch
# ---------------------------------------------------------------------------


def test_get_base_dir_returns_opt_bind_when_it_exists(monkeypatch):
    monkeypatch.setattr("os.path.exists", lambda p: p == "/opt/bind")
    from src.security import get_base_dir

    assert get_base_dir() == "/opt/bind"


# ---------------------------------------------------------------------------
# 2. _rotate_log_if_needed() — rotation branch
# ---------------------------------------------------------------------------


def test_rotate_log_trims_to_last_n_lines(tmp_path):
    from src.security import _rotate_log_if_needed

    log_file = tmp_path / "security.log"
    lines = [f"entry_{i}\n" for i in range(10)]
    log_file.write_text("".join(lines))

    _rotate_log_if_needed(str(log_file), max_lines=3)

    result = log_file.read_text().splitlines()
    assert len(result) == 3
    assert result[0] == "entry_7"
    assert result[-1] == "entry_9"


# ---------------------------------------------------------------------------
# 3. _migrate_credentials() — v1 → v2 migration body
# ---------------------------------------------------------------------------


def test_migrate_credentials_v1_to_v2(isolated_credentials):
    from src.security import _migrate_credentials

    v1 = {
        "version": 1,
        "username": "admin",
        "password_hash": "pbkdf2:sha256:abc",
        "created_at": "2024-01-01T00:00:00Z",
    }
    result = _migrate_credentials(v1)

    assert result["version"] == 2
    assert "failed_attempts" in result
    assert "locked_until" in result
    assert "last_login" in result
    assert "last_login_ip" in result


# ---------------------------------------------------------------------------
# 4. _save_credentials_raw() — OSError returns False
# ---------------------------------------------------------------------------


def test_save_credentials_raw_returns_false_on_oserror(isolated_credentials):
    from src.security import _save_credentials_raw

    with patch("src.security.open", side_effect=OSError("permission denied")):
        assert _save_credentials_raw({"version": 2}) is False


# ---------------------------------------------------------------------------
# 5. is_account_locked() — lockout expired branch
# ---------------------------------------------------------------------------


def test_is_account_locked_clears_expired_lockout(tmp_path, monkeypatch):
    import src.security as _sec

    creds_file = tmp_path / "creds.json"
    past_time = datetime.now(timezone.utc) - timedelta(hours=2)
    creds = {
        "version": 2,
        "username": "admin",
        "password_hash": "x",
        "failed_attempts": 5,
        "locked_until": past_time.isoformat(timespec="microseconds").replace("+00:00", "Z"),
    }
    creds_file.write_text(json.dumps(creds))
    monkeypatch.setattr(_sec, "CREDENTIALS_FILE", str(creds_file))

    is_locked, remaining = _sec.is_account_locked()

    assert is_locked is False
    assert remaining is None
    saved = json.loads(creds_file.read_text())
    assert saved["locked_until"] is None


# ---------------------------------------------------------------------------
# 6. is_account_locked() — ValueError / TypeError branch
# ---------------------------------------------------------------------------


def test_is_account_locked_returns_false_on_bad_timestamp(tmp_path, monkeypatch):
    import src.security as _sec

    creds_file = tmp_path / "creds.json"
    creds = {
        "version": 2,
        "username": "admin",
        "password_hash": "x",
        "failed_attempts": 0,
        "locked_until": "not-a-date",
    }
    creds_file.write_text(json.dumps(creds))
    monkeypatch.setattr(_sec, "CREDENTIALS_FILE", str(creds_file))

    is_locked, remaining = _sec.is_account_locked()

    assert is_locked is False
    assert remaining is None


# ---------------------------------------------------------------------------
# 7. get_allowed_networks() — env var branch
# ---------------------------------------------------------------------------


def test_get_allowed_networks_uses_env_var(monkeypatch):
    from src.security import get_allowed_networks

    monkeypatch.setenv("BIND_ALLOWED_IPS", "10.1.2.0/24,172.31.0.0/16")
    assert get_allowed_networks() == ["10.1.2.0/24", "172.31.0.0/16"]


# ---------------------------------------------------------------------------
# 8. is_ip_allowed() — invalid network in allowlist skipped
# ---------------------------------------------------------------------------


def test_is_ip_allowed_skips_invalid_cidr_entry(monkeypatch):
    from src.security import get_allowed_networks, is_ip_allowed

    monkeypatch.setattr(
        "src.security.get_allowed_networks",
        lambda: ["not-valid-cidr", "10.0.0.0/8"],
    )
    assert is_ip_allowed("10.0.0.1") is True


# ---------------------------------------------------------------------------
# 9. get_client_ip() — invalid remote_addr returns fallback
# ---------------------------------------------------------------------------


def test_get_client_ip_returns_fallback_on_invalid_remote_addr():
    from src.security import get_client_ip

    req = MagicMock()
    req.remote_addr = "not-an-ip"
    assert get_client_ip(req) == "0.0.0.0"
