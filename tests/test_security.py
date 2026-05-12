import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from src.security import (
    MAX_FAILED_ATTEMPTS,
    _rotate_log_if_needed,
    get_client_ip,
    is_account_locked,
    is_ip_allowed,
    load_credentials,
    record_failed_login,
    save_credentials,
    validate_password,
    verify_credentials,
)


class TestValidatePassword:
    def test_too_short(self):
        is_valid, msg = validate_password("short1!")
        assert is_valid is False
        assert "8" in msg

    def test_no_special_char(self):
        is_valid, msg = validate_password("Password")
        assert is_valid is False
        assert "number or special" in msg

    def test_valid(self):
        is_valid, msg = validate_password("Secure1!")
        assert is_valid is True
        assert msg == ""


class TestIsIpAllowed:
    def test_localhost_allowed(self):
        assert is_ip_allowed("127.0.0.1") is True

    def test_private_192_allowed(self):
        assert is_ip_allowed("192.168.1.50") is True

    def test_private_10_allowed(self):
        assert is_ip_allowed("10.0.0.1") is True

    def test_public_rejected(self):
        assert is_ip_allowed("8.8.8.8") is False

    def test_invalid_string_rejected(self):
        assert is_ip_allowed("not-an-ip") is False


class TestGetClientIp:
    def test_trusted_proxy_honours_xff(self):
        req = MagicMock()
        req.remote_addr = "127.0.0.1"
        req.headers.get = lambda k, default="": "203.0.113.1" if k == "X-Forwarded-For" else default
        assert get_client_ip(req) == "203.0.113.1"

    def test_untrusted_direct_ignores_xff(self):
        req = MagicMock()
        req.remote_addr = "203.0.113.5"
        req.headers.get = lambda k, default="": "10.0.0.1" if k == "X-Forwarded-For" else default
        assert get_client_ip(req) == "203.0.113.5"

    def test_none_request_returns_sentinel(self):
        assert get_client_ip(None) == "0.0.0.0"


class TestRotateLogIfNeeded:
    def test_under_limit_no_rotation(self, tmp_path):
        log_file = tmp_path / "security.log"
        lines = [f"line_{i}\n" for i in range(5)]
        log_file.write_text("".join(lines))
        _rotate_log_if_needed(str(log_file), max_lines=10)
        assert len(log_file.read_text().splitlines()) == 5

    def test_over_limit_trims_to_max(self, tmp_path):
        log_file = tmp_path / "security.log"
        lines = [f"line_{i}\n" for i in range(20)]
        log_file.write_text("".join(lines))
        _rotate_log_if_needed(str(log_file), max_lines=10)
        content = log_file.read_text().splitlines()
        assert len(content) == 10
        assert content[0] == "line_10"
        assert content[-1] == "line_19"


class TestCredentialLifecycle:
    @patch("src.security.get_client_ip", return_value="127.0.0.1")
    @patch("src.security.log_security_event")
    def test_invalid_username_rejected(self, mock_log, mock_ip, monkeypatch, tmp_path):
        monkeypatch.setattr("src.security.CREDENTIALS_FILE", str(tmp_path / "creds.json"))
        success, msg = save_credentials("ab", "Secure1!")
        assert success is False
        assert "Username" in msg

    @patch("src.security.get_client_ip", return_value="127.0.0.1")
    @patch("src.security.log_security_event")
    def test_weak_password_rejected(self, mock_log, mock_ip, monkeypatch, tmp_path):
        monkeypatch.setattr("src.security.CREDENTIALS_FILE", str(tmp_path / "creds.json"))
        success, msg = save_credentials("admin", "weak")
        assert success is False

    @patch("src.security.get_client_ip", return_value="127.0.0.1")
    @patch("src.security.log_security_event")
    def test_save_then_load(self, mock_log, mock_ip, monkeypatch, tmp_path):
        monkeypatch.setattr("src.security.CREDENTIALS_FILE", str(tmp_path / "creds.json"))
        success, _ = save_credentials("admin", "Secure1!")
        assert success is True
        creds = load_credentials()
        assert creds["username"] == "admin"
        assert "password_hash" in creds

    def test_load_missing_file_returns_empty(self, monkeypatch, tmp_path):
        monkeypatch.setattr("src.security.CREDENTIALS_FILE", str(tmp_path / "does_not_exist.json"))
        assert load_credentials() == {}

    def test_load_corrupt_json_returns_empty(self, monkeypatch, tmp_path):
        creds_file = tmp_path / "creds.json"
        creds_file.write_text("not valid json")
        monkeypatch.setattr("src.security.CREDENTIALS_FILE", str(creds_file))
        assert load_credentials() == {}


class TestAccountLockout:
    def setup_method(self):
        self.minimal_creds = {
            "version": 2,
            "username": "admin",
            "password_hash": "x",
            "failed_attempts": 0,
            "locked_until": None,
        }

    def test_not_locked_when_no_locked_until(self, monkeypatch, tmp_path):
        creds_file = tmp_path / "creds.json"
        creds_file.write_text(json.dumps(self.minimal_creds))
        monkeypatch.setattr("src.security.CREDENTIALS_FILE", str(creds_file))
        is_locked, _ = is_account_locked()
        assert is_locked is False

    def test_locked_when_future_timestamp(self, monkeypatch, tmp_path):
        creds_file = tmp_path / "creds.json"
        future_time = datetime.now(timezone.utc) + timedelta(minutes=10)
        self.minimal_creds["locked_until"] = future_time.isoformat(timespec="microseconds").replace(
            "+00:00", "Z"
        )
        creds_file.write_text(json.dumps(self.minimal_creds))
        monkeypatch.setattr("src.security.CREDENTIALS_FILE", str(creds_file))
        is_locked, minutes = is_account_locked()
        assert is_locked is True
        assert minutes > 0

    def test_expired_lock_is_cleared(self, monkeypatch, tmp_path):
        creds_file = tmp_path / "creds.json"
        past_time = datetime.now(timezone.utc) - timedelta(minutes=1)
        self.minimal_creds["locked_until"] = past_time.isoformat(timespec="microseconds").replace(
            "+00:00", "Z"
        )
        creds_file.write_text(json.dumps(self.minimal_creds))
        monkeypatch.setattr("src.security.CREDENTIALS_FILE", str(creds_file))
        is_locked, _ = is_account_locked()
        assert is_locked is False
        creds = json.loads(creds_file.read_text())
        assert creds["locked_until"] is None

    @patch("src.security.get_client_ip", return_value="1.2.3.4")
    @patch("src.security.log_security_event")
    def test_lockout_triggered_after_max_attempts(self, mock_log, mock_ip, monkeypatch, tmp_path):
        creds_file = tmp_path / "creds.json"
        creds_file.write_text(json.dumps(self.minimal_creds))
        monkeypatch.setattr("src.security.CREDENTIALS_FILE", str(creds_file))
        for _ in range(MAX_FAILED_ATTEMPTS):
            record_failed_login("1.2.3.4")
        creds = json.loads(creds_file.read_text())
        assert creds["locked_until"] is not None


class TestVerifyCredentials:
    @patch("src.security.get_client_ip", return_value="127.0.0.1")
    @patch("src.security.log_security_event")
    def test_correct_credentials_returns_true(self, mock_log, mock_ip, monkeypatch, tmp_path):
        monkeypatch.setattr("src.security.CREDENTIALS_FILE", str(tmp_path / "creds.json"))
        save_credentials("admin", "Secure1!")
        assert verify_credentials("admin", "Secure1!", ip="127.0.0.1") is True

    @patch("src.security.get_client_ip", return_value="127.0.0.1")
    @patch("src.security.log_security_event")
    def test_wrong_password_returns_false(self, mock_log, mock_ip, monkeypatch, tmp_path):
        monkeypatch.setattr("src.security.CREDENTIALS_FILE", str(tmp_path / "creds.json"))
        save_credentials("admin", "Secure1!")
        assert verify_credentials("admin", "WrongPass1!", ip="127.0.0.1") is False

    @patch("src.security.get_client_ip", return_value="127.0.0.1")
    @patch("src.security.log_security_event")
    def test_wrong_username_returns_false(self, mock_log, mock_ip, monkeypatch, tmp_path):
        monkeypatch.setattr("src.security.CREDENTIALS_FILE", str(tmp_path / "creds.json"))
        save_credentials("admin", "Secure1!")
        assert verify_credentials("wronguser", "Secure1!", ip="127.0.0.1") is False
