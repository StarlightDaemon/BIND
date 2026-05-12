import subprocess
from unittest.mock import MagicMock, patch

from src.config_manager import ConfigManager


class TestReadConfig:
    def test_returns_defaults_when_file_missing(self, tmp_path):
        cm = ConfigManager(config_path=str(tmp_path / "config.env"))
        config = cm.read_config()
        assert config.keys() == ConfigManager.DEFAULTS.keys()
        for k, v in ConfigManager.DEFAULTS.items():
            assert config[k] == v

    def test_parses_known_keys(self, tmp_path):
        config_file = tmp_path / "config.env"
        config_file.write_text("SCRAPE_INTERVAL=30\nMAGNETS_DIR=custom/path\n")
        cm = ConfigManager(config_path=str(config_file))
        config = cm.read_config()
        assert config["SCRAPE_INTERVAL"] == "30"
        assert config["MAGNETS_DIR"] == "custom/path"

    def test_skips_comments_and_blank_lines(self, tmp_path):
        config_file = tmp_path / "config.env"
        config_file.write_text("# comment\n\nSCRAPE_INTERVAL=45\n")
        cm = ConfigManager(config_path=str(config_file))
        config = cm.read_config()
        assert config["SCRAPE_INTERVAL"] == "45"

    def test_ignores_unknown_keys(self, tmp_path):
        config_file = tmp_path / "config.env"
        config_file.write_text("UNKNOWN_KEY=value\nSCRAPE_INTERVAL=20\n")
        cm = ConfigManager(config_path=str(config_file))
        config = cm.read_config()
        assert config["SCRAPE_INTERVAL"] == "20"
        assert "UNKNOWN_KEY" not in config


class TestWriteConfig:
    def test_validation_failure_returns_false(self, tmp_path):
        cm = ConfigManager(config_path=str(tmp_path / "config.env"))
        success, msg = cm.write_config({"SCRAPE_INTERVAL": "5"})
        assert success is False
        assert "15" in msg

    def test_success_writes_file_and_returns_true(self, tmp_path):
        config_file = tmp_path / "config.env"
        cm = ConfigManager(config_path=str(config_file))
        success, msg = cm.write_config({"ABB_URL": "http://example.com", "SCRAPE_INTERVAL": "30"})
        assert success is True
        assert msg == "Configuration saved successfully."
        content = config_file.read_text()
        assert "SCRAPE_INTERVAL=30" in content
        assert "ABB_URL=http://example.com" in content

    def test_oserror_on_write_returns_false(self, tmp_path):
        cm = ConfigManager(config_path=str(tmp_path / "config.env"))
        with patch("builtins.open", side_effect=OSError("disk full")):
            success, msg = cm.write_config({"SCRAPE_INTERVAL": "30"})
            assert success is False
            assert "disk full" in msg


class TestValidate:
    def test_integer_in_range(self):
        cm = ConfigManager()
        is_valid, msg = cm._validate("SCRAPE_INTERVAL", "60")
        assert is_valid is True
        assert msg == ""

    def test_integer_below_min(self):
        cm = ConfigManager()
        is_valid, msg = cm._validate("SCRAPE_INTERVAL", "5")
        assert is_valid is False
        assert "15" in msg

    def test_integer_above_max(self):
        cm = ConfigManager()
        is_valid, msg = cm._validate("SCRAPE_INTERVAL", "9999")
        assert is_valid is False
        assert "must be between" in msg

    def test_integer_non_numeric(self):
        cm = ConfigManager()
        is_valid, msg = cm._validate("SCRAPE_INTERVAL", "abc")
        assert is_valid is False
        assert "integer" in msg

    def test_url_empty(self):
        cm = ConfigManager()
        is_valid, msg = cm._validate("ABB_URL", "")
        assert is_valid is False
        assert "empty" in msg

    def test_url_valid_https(self):
        cm = ConfigManager()
        is_valid, msg = cm._validate("ABB_URL", "https://example.com")
        assert is_valid is True
        assert msg == ""

    def test_url_missing_scheme(self):
        cm = ConfigManager()
        is_valid, msg = cm._validate("ABB_URL", "example.com")
        assert is_valid is False
        assert "must be a valid HTTP/HTTPS URL" in msg

    def test_url_optional_empty_allowed(self):
        cm = ConfigManager()
        is_valid, msg = cm._validate("BASE_URL", "")
        assert is_valid is True
        assert msg == ""

    def test_url_optional_valid(self):
        cm = ConfigManager()
        is_valid, msg = cm._validate("BASE_URL", "http://bind.example.com")
        assert is_valid is True
        assert msg == ""

    def test_url_optional_invalid(self):
        cm = ConfigManager()
        is_valid, msg = cm._validate("BASE_URL", "not-a-url")
        assert is_valid is False
        assert "must be a valid HTTP/HTTPS URL or empty" in msg

    def test_proxy_empty_allowed(self):
        cm = ConfigManager()
        is_valid, msg = cm._validate("BIND_PROXY", "")
        assert is_valid is True
        assert msg == ""

    def test_proxy_socks5(self):
        cm = ConfigManager()
        is_valid, msg = cm._validate("BIND_PROXY", "socks5://user:pass@proxy:1080")
        assert is_valid is True
        assert msg == ""

    def test_proxy_http(self):
        cm = ConfigManager()
        is_valid, msg = cm._validate("BIND_PROXY", "http://proxy:8080")
        assert is_valid is True
        assert msg == ""

    def test_proxy_invalid_scheme(self):
        cm = ConfigManager()
        is_valid, msg = cm._validate("BIND_PROXY", "ftp://proxy:21")
        assert is_valid is False
        assert "valid proxy URL" in msg


class TestRestartDaemon:
    @patch("subprocess.run")
    def test_file_not_found_returns_false(self, mock_run, tmp_path):
        mock_run.side_effect = FileNotFoundError()
        cm = ConfigManager(config_path=str(tmp_path / "config.env"))
        success, msg = cm.restart_daemon()
        assert success is False
        assert "systemctl not found. Running in development mode?" in msg

    @patch("subprocess.run")
    def test_timeout_returns_false(self, mock_run, tmp_path):
        def side_effect(*args, **kwargs):
            if args[0] == ["systemctl", "daemon-reload"]:
                return MagicMock()
            raise subprocess.TimeoutExpired("cmd", 30)

        mock_run.side_effect = side_effect
        cm = ConfigManager(config_path=str(tmp_path / "config.env"))
        success, msg = cm.restart_daemon()
        assert success is False
        assert "Daemon restart timed out." in msg

    @patch("subprocess.run")
    def test_called_process_error_returns_false(self, mock_run, tmp_path):
        def side_effect(*args, **kwargs):
            if args[0] == ["systemctl", "daemon-reload"]:
                return MagicMock()
            raise subprocess.CalledProcessError(1, "cmd", stderr=b"unit error")

        mock_run.side_effect = side_effect
        cm = ConfigManager(config_path=str(tmp_path / "config.env"))
        success, msg = cm.restart_daemon()
        assert success is False
        assert "unit error" in msg

    @patch("subprocess.run")
    def test_success_returns_true(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock()
        cm = ConfigManager(config_path=str(tmp_path / "config.env"))
        success, msg = cm.restart_daemon()
        assert success is True
        assert "Daemon restarted successfully." in msg
