from unittest.mock import patch

from click.testing import CliRunner
from src.bind import cli


def test_permission_error_on_makedirs_exits_1(tmp_path):
    with patch.dict("os.environ", {"TEST_KEY_1": "old_value"}, clear=True):
        with (
            patch("src.bind.ConfigManager") as mock_cm,
            patch("src.bind.BindScraper"),
            patch("src.bind.TrackerManager"),
        ):
            mock_cm.return_value.read_config.return_value = {
                "TEST_KEY_1": "123",
                "TEST_KEY_2": "456",
            }
            with patch("os.makedirs", side_effect=PermissionError):
                result = CliRunner().invoke(cli, ["daemon", "--output-dir", "/no/permission"])
        assert result.exit_code == 1


def test_oserror_on_makedirs_exits_1(tmp_path):
    with patch.dict("os.environ", {"TEST_KEY_1": "old_value"}, clear=True):
        with (
            patch("src.bind.ConfigManager") as mock_cm,
            patch("src.bind.BindScraper"),
            patch("src.bind.TrackerManager"),
        ):
            mock_cm.return_value.read_config.return_value = {
                "TEST_KEY_1": "123",
                "TEST_KEY_2": "456",
            }
            with patch("os.makedirs", side_effect=OSError("disk full")):
                result = CliRunner().invoke(cli, ["daemon", "--output-dir", "/bad/path"])
        assert result.exit_code == 1
