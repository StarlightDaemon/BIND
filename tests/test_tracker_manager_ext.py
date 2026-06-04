from unittest.mock import patch

import pytest
from src.core.tracker_manager import TrackerManager


def test_load_returns_defaults_when_file_missing(tmp_path):
    tm = TrackerManager(str(tmp_path))
    # Delete the file that __init__ just created
    tm.path.unlink()
    result = tm.load()
    assert result == TrackerManager.DEFAULT_TRACKERS


def test_get_default_trackers_returns_defaults(tmp_path):
    tm = TrackerManager(str(tmp_path))
    assert tm.get_default_trackers() == TrackerManager.DEFAULT_TRACKERS


def test_save_raises_and_cleans_up_tmp_on_oserror(tmp_path):
    tm = TrackerManager(str(tmp_path))
    with patch("os.replace", side_effect=OSError("no space")):
        with pytest.raises(OSError, match="no space"):
            tm.save(["udp://tracker.example.com:1337"])
    # tmp file should be cleaned up
    assert not tm.path.with_suffix(".json.tmp").exists()


def test_save_oserror_leaves_no_tmp_when_remove_also_fails(tmp_path):
    tm = TrackerManager(str(tmp_path))
    with patch("os.replace", side_effect=OSError("no space")):
        with patch("os.remove", side_effect=OSError("also broken")):
            with pytest.raises(OSError):
                tm.save(["udp://tracker.example.com:1337"])
