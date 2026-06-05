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


# ---------------------------------------------------------------------------
# Additional coverage: edge-case branches in src/security.py
# ---------------------------------------------------------------------------
import pytest  # noqa: E402


class TestGetBaseDirOptBind:
    def test_returns_opt_bind_when_exists(self, monkeypatch):
        import src.security as _sec

        monkeypatch.setattr(_sec.os.path, "exists", lambda p: p == "/opt/bind")
        assert _sec.get_base_dir() == "/opt/bind"


class TestGetSecurityLogPath:
    def test_path_under_base_dir(self, monkeypatch, tmp_path):
        import src.security as _sec

        monkeypatch.setattr(_sec, "get_base_dir", lambda: str(tmp_path))
        assert _sec.get_security_log_path() == str(tmp_path / "logs" / "security.log")


class TestLogSecurityEvent:
    def test_writes_event_to_file(self, tmp_path, monkeypatch):
        import src.security as _sec

        log_file = tmp_path / "security.log"
        monkeypatch.setattr(_sec, "get_security_log_path", lambda: str(log_file))
        _sec.log_security_event("LOGIN_SUCCESS", "admin", "127.0.0.1")
        content = log_file.read_text()
        assert "LOGIN_SUCCESS" in content
        assert "admin" in content

    def test_details_appended_when_provided(self, tmp_path, monkeypatch):
        import src.security as _sec

        log_file = tmp_path / "security.log"
        monkeypatch.setattr(_sec, "get_security_log_path", lambda: str(log_file))
        _sec.log_security_event("LOGIN_FAILED", "admin", "1.2.3.4", "attempt=3")
        assert "attempt=3" in log_file.read_text()

    def test_oserror_on_write_silenced(self, monkeypatch):
        import src.security as _sec

        monkeypatch.setattr(_sec, "get_security_log_path", lambda: "/no/such/path/sec.log")
        _sec.log_security_event("LOGIN_SUCCESS", "admin", "127.0.0.1")  # must not raise


class TestRotateLogOsError:
    def test_nonexistent_path_silenced(self):
        _rotate_log_if_needed("/no/such/path/security.log", max_lines=10)  # must not raise


class TestCredentialMigration:
    def test_v1_creds_migrated_on_load(self, monkeypatch, tmp_path):
        import src.security as _sec

        creds_file = tmp_path / "creds.json"
        v1 = {"username": "admin", "password_hash": "hash", "created_at": "2024-01-01T00:00:00Z"}
        creds_file.write_text(json.dumps(v1))
        monkeypatch.setattr(_sec, "CREDENTIALS_FILE", str(creds_file))
        result = _sec.load_credentials()
        assert result["version"] == 2
        assert "failed_attempts" in result
        assert "locked_until" in result
        assert "last_login" in result
        assert result["last_login_ip"] is None

    def test_migrate_preserves_username(self):
        import src.security as _sec

        v1 = {"username": "admin", "password_hash": "hash", "created_at": "2024-01-01T00:00:00Z"}
        with patch("src.security._save_credentials_raw", return_value=True):
            result = _sec._migrate_credentials(v1)
        assert result["username"] == "admin"
        assert result["version"] == 2


class TestSaveCredentialsRawOsError:
    def test_returns_false_when_directory_missing(self, monkeypatch, tmp_path):
        import src.security as _sec

        monkeypatch.setattr(_sec, "CREDENTIALS_FILE", str(tmp_path / "missing_dir" / "creds.json"))
        assert _sec._save_credentials_raw({"version": 2}) is False


class TestSaveCredentialsSaveFails:
    def test_returns_failure_message(self, monkeypatch, tmp_path):
        import src.security as _sec

        monkeypatch.setattr(_sec, "CREDENTIALS_FILE", str(tmp_path / "creds.json"))
        with patch("src.security._save_credentials_raw", return_value=False):
            success, msg = _sec.save_credentials("admin", "Secure1!")
        assert success is False
        assert "Failed" in msg


class TestChangePassword:
    def _write_creds(self, creds_file, password="Secure1!"):
        from werkzeug.security import generate_password_hash as _gph

        creds = {
            "version": 2,
            "username": "admin",
            "password_hash": _gph(password),
            "failed_attempts": 0,
            "locked_until": None,
            "last_login": None,
            "last_login_ip": None,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        creds_file.write_text(json.dumps(creds))

    @patch("src.security.log_security_event")
    @patch("src.security.get_client_ip", return_value="127.0.0.1")
    def test_no_creds_returns_error(self, mock_ip, mock_log, monkeypatch, tmp_path):
        import src.security as _sec

        monkeypatch.setattr(_sec, "CREDENTIALS_FILE", str(tmp_path / "none.json"))
        ok, msg = _sec.change_password("old", "NewSecure1!")
        assert ok is False
        assert "No credentials" in msg

    @patch("src.security.log_security_event")
    @patch("src.security.get_client_ip", return_value="127.0.0.1")
    def test_wrong_current_password_rejected(self, mock_ip, mock_log, monkeypatch, tmp_path):
        import src.security as _sec

        creds_file = tmp_path / "creds.json"
        self._write_creds(creds_file)
        monkeypatch.setattr(_sec, "CREDENTIALS_FILE", str(creds_file))
        ok, msg = _sec.change_password("WrongOld1!", "NewSecure1!")
        assert ok is False
        assert "incorrect" in msg

    @patch("src.security.log_security_event")
    @patch("src.security.get_client_ip", return_value="127.0.0.1")
    def test_weak_new_password_rejected(self, mock_ip, mock_log, monkeypatch, tmp_path):
        import src.security as _sec

        creds_file = tmp_path / "creds.json"
        self._write_creds(creds_file)
        monkeypatch.setattr(_sec, "CREDENTIALS_FILE", str(creds_file))
        ok, _ = _sec.change_password("Secure1!", "weak")
        assert ok is False

    @patch("src.security.log_security_event")
    @patch("src.security.get_client_ip", return_value="127.0.0.1")
    def test_save_fail_returns_error(self, mock_ip, mock_log, monkeypatch, tmp_path):
        import src.security as _sec

        creds_file = tmp_path / "creds.json"
        self._write_creds(creds_file)
        monkeypatch.setattr(_sec, "CREDENTIALS_FILE", str(creds_file))
        with patch("src.security._save_credentials_raw", return_value=False):
            ok, msg = _sec.change_password("Secure1!", "NewSecure1!")
        assert ok is False
        assert "Failed" in msg


class TestIsAccountLockedParseError:
    def test_invalid_locked_until_returns_not_locked(self, monkeypatch, tmp_path):
        import src.security as _sec

        creds_file = tmp_path / "creds.json"
        creds = {
            "version": 2,
            "username": "admin",
            "password_hash": "x",
            "failed_attempts": 0,
            "locked_until": "not-a-datetime",
        }
        creds_file.write_text(json.dumps(creds))
        monkeypatch.setattr(_sec, "CREDENTIALS_FILE", str(creds_file))
        is_locked, _ = _sec.is_account_locked()
        assert is_locked is False


class TestRecordFailedLoginNoCreds:
    def test_empty_creds_returns_silently(self, monkeypatch, tmp_path):
        import src.security as _sec

        monkeypatch.setattr(_sec, "CREDENTIALS_FILE", str(tmp_path / "none.json"))
        _sec.record_failed_login("127.0.0.1")  # must not raise


class TestRecordSuccessfulLoginNoCreds:
    def test_empty_creds_returns_silently(self, monkeypatch, tmp_path):
        import src.security as _sec

        monkeypatch.setattr(_sec, "CREDENTIALS_FILE", str(tmp_path / "none.json"))
        _sec.record_successful_login("127.0.0.1")  # must not raise


class TestVerifyCredentialsEdgeCases:
    def test_no_creds_returns_false(self, monkeypatch, tmp_path):
        import src.security as _sec

        monkeypatch.setattr(_sec, "CREDENTIALS_FILE", str(tmp_path / "none.json"))
        assert _sec.verify_credentials("admin", "Secure1!") is False

    @patch("src.security.log_security_event")
    def test_locked_account_returns_false(self, mock_log, monkeypatch, tmp_path):
        import src.security as _sec
        from werkzeug.security import generate_password_hash as _gph

        creds_file = tmp_path / "creds.json"
        future = (
            (datetime.now(timezone.utc) + timedelta(minutes=10))
            .isoformat(timespec="microseconds")
            .replace("+00:00", "Z")
        )
        creds = {
            "version": 2,
            "username": "admin",
            "password_hash": _gph("Secure1!"),
            "failed_attempts": 5,
            "locked_until": future,
            "last_login": None,
            "last_login_ip": None,
        }
        creds_file.write_text(json.dumps(creds))
        monkeypatch.setattr(_sec, "CREDENTIALS_FILE", str(creds_file))
        assert _sec.verify_credentials("admin", "Secure1!", ip="127.0.0.1") is False


class TestGetAllowedNetworksEnv:
    def test_env_var_overrides_defaults(self, monkeypatch):
        import src.security as _sec

        monkeypatch.setenv("BIND_ALLOWED_IPS", "192.168.1.0/24,10.0.0.0/8")
        assert _sec.get_allowed_networks() == ["192.168.1.0/24", "10.0.0.0/8"]


class TestIsIpAllowedInvalidNetwork:
    def test_invalid_network_in_list_is_skipped(self, monkeypatch):
        monkeypatch.setenv("BIND_ALLOWED_IPS", "not-a-cidr,192.168.1.0/24")
        assert is_ip_allowed("192.168.1.50") is True


class TestGetClientIpEdgeCases:
    def test_invalid_remote_addr_returns_sentinel(self):
        req = MagicMock()
        req.remote_addr = "not-an-ip"
        assert get_client_ip(req) == "0.0.0.0"

    def test_trusted_proxy_no_xff_returns_direct_ip(self):
        req = MagicMock()
        req.remote_addr = "127.0.0.1"
        req.headers.get = lambda k, default="": ""
        assert get_client_ip(req) == "127.0.0.1"


class TestIpAllowlistMiddleware:
    def _make_app(self):
        import src.security as _sec
        from flask import Flask

        app = Flask(__name__)
        app.config["TESTING"] = True
        _sec.ip_allowlist_middleware(app)

        @app.route("/probe")
        def probe():
            return "ok"

        return app

    def test_filter_disabled_allows_any_ip(self, monkeypatch):
        monkeypatch.setenv("BIND_IP_FILTER", "false")
        resp = self._make_app().test_client().get("/probe", environ_base={"REMOTE_ADDR": "8.8.8.8"})
        assert resp.status_code == 200

    def test_blocked_ip_returns_403(self, monkeypatch):
        monkeypatch.setenv("BIND_IP_FILTER", "true")
        monkeypatch.setenv("BIND_ALLOWED_IPS", "192.168.1.0/24")
        resp = self._make_app().test_client().get("/probe", environ_base={"REMOTE_ADDR": "8.8.8.8"})
        assert resp.status_code == 403


class TestCheckAuth:
    def _write_creds(self, tmp_path, locked=False):
        from werkzeug.security import generate_password_hash as _gph

        locked_until = None
        if locked:
            locked_until = (
                (datetime.now(timezone.utc) + timedelta(minutes=10))
                .isoformat(timespec="microseconds")
                .replace("+00:00", "Z")
            )
        creds = {
            "version": 2,
            "username": "admin",
            "password_hash": _gph("Secure1!"),
            "failed_attempts": 5 if locked else 0,
            "locked_until": locked_until,
            "last_login": None,
            "last_login_ip": None,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        creds_file = tmp_path / "creds.json"
        creds_file.write_text(json.dumps(creds))
        return creds_file

    @patch("src.security.log_security_event")
    def test_locked_account_returns_false(self, mock_log, monkeypatch, tmp_path):
        import src.security as _sec
        from flask import Flask

        creds_file = self._write_creds(tmp_path, locked=True)
        monkeypatch.setattr(_sec, "CREDENTIALS_FILE", str(creds_file))
        app = Flask(__name__)
        with app.test_request_context("/"):
            assert _sec.check_auth("admin", "Secure1!") is False

    @patch("src.security.log_security_event")
    def test_setup_complete_valid_creds_returns_true(self, mock_log, monkeypatch, tmp_path):
        import src.security as _sec
        from flask import Flask

        creds_file = self._write_creds(tmp_path)
        monkeypatch.setattr(_sec, "CREDENTIALS_FILE", str(creds_file))
        app = Flask(__name__)
        with app.test_request_context("/"):
            assert _sec.check_auth("admin", "Secure1!") is True


class TestRequiresAuth:
    @pytest.fixture
    def auth_client(self, tmp_path, monkeypatch):
        import src.security as _sec
        from flask import Flask
        from werkzeug.security import generate_password_hash as _gph

        monkeypatch.setenv("BIND_AUTH_ENABLED", "true")
        creds_file = tmp_path / "creds.json"
        creds = {
            "version": 2,
            "username": "admin",
            "password_hash": _gph("Secure1!"),
            "failed_attempts": 0,
            "locked_until": None,
            "last_login": None,
            "last_login_ip": None,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        creds_file.write_text(json.dumps(creds))
        monkeypatch.setattr(_sec, "CREDENTIALS_FILE", str(creds_file))
        monkeypatch.setattr(_sec, "log_security_event", lambda *a, **kw: None)

        app = Flask(__name__)
        app.config["TESTING"] = True

        @app.route("/protected")
        @_sec.requires_auth
        def protected():
            return "ok", 200

        return app.test_client()

    def test_no_auth_returns_401(self, auth_client):
        assert auth_client.get("/protected").status_code == 401

    def test_wrong_password_returns_401(self, auth_client):
        import base64

        token = base64.b64encode(b"admin:WrongPass1!").decode()
        resp = auth_client.get("/protected", headers={"Authorization": f"Basic {token}"})
        assert resp.status_code == 401

    def test_correct_credentials_returns_200(self, auth_client):
        import base64

        token = base64.b64encode(b"admin:Secure1!").decode()
        resp = auth_client.get("/protected", headers={"Authorization": f"Basic {token}"})
        assert resp.status_code == 200

    def test_locked_account_returns_403(self, tmp_path, monkeypatch):
        import src.security as _sec
        from flask import Flask

        monkeypatch.setenv("BIND_AUTH_ENABLED", "true")
        creds_file = tmp_path / "locked.json"
        future = (
            (datetime.now(timezone.utc) + timedelta(minutes=10))
            .isoformat(timespec="microseconds")
            .replace("+00:00", "Z")
        )
        creds = {
            "version": 2,
            "username": "admin",
            "password_hash": "x",
            "failed_attempts": 5,
            "locked_until": future,
            "last_login": None,
            "last_login_ip": None,
        }
        creds_file.write_text(json.dumps(creds))
        monkeypatch.setattr(_sec, "CREDENTIALS_FILE", str(creds_file))

        app = Flask(__name__)
        app.config["TESTING"] = True

        @app.route("/protected")
        @_sec.requires_auth
        def protected():
            return "ok", 200

        assert app.test_client().get("/protected").status_code == 403


class TestRemainingBranches:
    """Five small tests for the last uncovered branches."""

    # 145->157: _migrate_credentials with version already >= 2 skips the if block
    def test_migrate_already_v2_returns_unchanged(self):
        import src.security as _sec

        v2 = {
            "version": 2,
            "username": "admin",
            "password_hash": "x",
            "failed_attempts": 0,
            "locked_until": None,
        }
        result = _sec._migrate_credentials(v2.copy())
        assert result["version"] == 2
        assert result["username"] == "admin"

    # 270-273: change_password success path (log + return True)
    @patch("src.security.log_security_event")
    @patch("src.security.get_client_ip", return_value="127.0.0.1")
    def test_change_password_success(self, mock_ip, mock_log, monkeypatch, tmp_path):
        import src.security as _sec
        from werkzeug.security import generate_password_hash as _gph

        creds_file = tmp_path / "creds.json"
        creds = {
            "version": 2,
            "username": "admin",
            "password_hash": _gph("Secure1!"),
            "failed_attempts": 0,
            "locked_until": None,
            "last_login": None,
            "last_login_ip": None,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        creds_file.write_text(json.dumps(creds))
        monkeypatch.setattr(_sec, "CREDENTIALS_FILE", str(creds_file))
        ok, msg = _sec.change_password("Secure1!", "NewSecure2@")
        assert ok is True
        assert "changed" in msg.lower()

    # 478: check_ip_allowlist returns None when IP is allowed
    def test_allowlist_allowed_ip_passes(self, monkeypatch):
        import src.security as _sec
        from flask import Flask

        monkeypatch.setenv("BIND_IP_FILTER", "true")
        monkeypatch.setenv("BIND_ALLOWED_IPS", "127.0.0.1/32")
        app = Flask(__name__)
        app.config["TESTING"] = True
        _sec.ip_allowlist_middleware(app)

        @app.route("/probe")
        def probe():
            return "ok"

        resp = app.test_client().get("/probe", environ_base={"REMOTE_ADDR": "127.0.0.1"})
        assert resp.status_code == 200

    # 504: check_auth returns False when setup is not complete
    def test_check_auth_setup_not_complete_returns_false(self, monkeypatch, tmp_path):
        import src.security as _sec
        from flask import Flask

        monkeypatch.setattr(_sec, "CREDENTIALS_FILE", str(tmp_path / "no_creds.json"))
        app = Flask(__name__)
        with app.test_request_context("/"):
            assert _sec.check_auth("admin", "Secure1!") is False

    # 523: requires_auth skips auth when BIND_AUTH_ENABLED=false
    def test_requires_auth_disabled_passes_through(self, monkeypatch):
        import src.security as _sec
        from flask import Flask

        monkeypatch.setenv("BIND_AUTH_ENABLED", "false")
        app = Flask(__name__)
        app.config["TESTING"] = True

        @app.route("/open")
        @_sec.requires_auth
        def open_route():
            return "ok", 200

        resp = app.test_client().get("/open")
        assert resp.status_code == 200
