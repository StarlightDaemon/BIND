import json

from src.core.tracker_manager import TrackerManager


def test_tracker_manager_init_defaults(tmp_path):
    """Test that defaults are loaded when file is missing."""
    magnets_dir = tmp_path / "magnets"
    magnets_dir.mkdir()

    tm = TrackerManager(str(magnets_dir))
    assert tm.get_trackers() == tm.DEFAULT_TRACKERS
    assert tm.path.exists()


def test_tracker_manager_normalization(tmp_path):
    """Test normalization: trim, dedupe, protocol validation."""
    magnets_dir = tmp_path / "magnets"
    magnets_dir.mkdir()
    tm = TrackerManager(str(magnets_dir))

    trackers = [
        "  udp://tracker.example.com  ",
        "UDP://tracker.example.com",  # Duplicate (case-insensitive)
        "http://tracker2.example.com",
        "ftp://invalid.com",  # Invalid protocol
        "https://tracker3.example.com",
        "   ",  # Empty
    ]

    normalized = tm.normalize(trackers)
    assert normalized == [
        "udp://tracker.example.com",
        "http://tracker2.example.com",
        "https://tracker3.example.com",
    ]


def test_tracker_manager_save_load(tmp_path):
    """Test atomic save and load."""
    magnets_dir = tmp_path / "magnets"
    magnets_dir.mkdir()
    tm = TrackerManager(str(magnets_dir))

    new_trackers = ["udp://new.tracker.com", "http://another.one"]

    tm.save(new_trackers)

    # Reload from disk
    tm2 = TrackerManager(str(magnets_dir))
    assert tm2.get_trackers() == new_trackers

    # Verify file content
    with open(tm.path) as f:
        data = json.load(f)
        assert data == new_trackers


def test_tracker_manager_set_from_text(tmp_path):
    """Test parsing from raw text block."""
    magnets_dir = tmp_path / "magnets"
    magnets_dir.mkdir()
    tm = TrackerManager(str(magnets_dir))

    text = """
    udp://tracker1.com

    http://tracker2.com
    udp://tracker1.com
    """

    tm.set_trackers_from_text(text)
    assert tm.get_trackers() == ["udp://tracker1.com", "http://tracker2.com"]


def test_tracker_manager_error_handling(tmp_path):
    """Test handling of malformed JSON."""
    magnets_dir = tmp_path / "magnets"
    magnets_dir.mkdir()
    tm = TrackerManager(str(magnets_dir))

    # Corrupt the file
    with open(tm.path, "w") as f:
        f.write("not json")

    # Should fallback to defaults
    assert tm.load() == tm.DEFAULT_TRACKERS


def test_tracker_manager_creates_missing_parent_directory(tmp_path):
    """
    REGRESSION TEST: TrackerManager should create parent directory if missing.

    This test covers the CI failure scenario where pytest collection failed
    because importing src.rss_server triggered TrackerManager initialization,
    which tried to write to data/trackers.json.tmp when the data/ directory
    did not exist.

    The fix ensures self.path.parent.mkdir(parents=True, exist_ok=True)
    is called in save() before attempting to open the file.
    """
    # Create a path with NON-EXISTENT parent directory
    # This simulates a fresh CI environment where data/ doesn't exist yet
    magnets_dir = tmp_path / "nonexistent_data" / "magnets"

    # Do NOT create the directory - this is the critical test condition
    # Old code would fail here with: FileNotFoundError: [Errno 2] No such file or directory: 'data/trackers.json.tmp'
    tm = TrackerManager(str(magnets_dir))

    # Verify the trackers.json file was created successfully
    expected_path = magnets_dir.parent / "trackers.json"
    assert expected_path.exists(), (
        "trackers.json should be created even when parent directory is missing"
    )

    # Verify contents are valid and contain default trackers
    with open(expected_path) as f:
        data = json.load(f)

    assert isinstance(data, list), "trackers.json should contain a list"
    assert len(data) > 0, "Default trackers should be saved"
    assert data == tm.DEFAULT_TRACKERS, "Should contain default trackers"
