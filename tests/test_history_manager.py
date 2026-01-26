"""Tests for HistoryManager class - global deduplication of magnet hashes."""
import os

from src.bind import HistoryManager


class TestHistoryManager:
    """Test suite for HistoryManager persistent deduplication."""

    def test_init_creates_empty_set(self, temp_magnets_dir):
        """New manager should start with empty seen set."""
        manager = HistoryManager(temp_magnets_dir)
        assert len(manager.seen) == 0
        assert manager.filepath.endswith("history.log")

    def test_add_and_exists(self, temp_magnets_dir):
        """Added hashes should be detectable via exists()."""
        manager = HistoryManager(temp_magnets_dir)

        assert manager.exists("abc123") is False
        manager.add("abc123")
        assert manager.exists("abc123") is True
        assert manager.exists("xyz789") is False

    def test_add_writes_to_file(self, temp_magnets_dir):
        """Adding a hash should persist it to disk."""
        manager = HistoryManager(temp_magnets_dir)
        manager.add("persistent_hash")

        # Verify file was created and contains the hash
        assert os.path.exists(manager.filepath)
        with open(manager.filepath) as f:
            contents = f.read()
        assert "persistent_hash" in contents

    def test_persistence_across_instances(self, temp_magnets_dir):
        """New manager instance should load previously saved hashes."""
        manager1 = HistoryManager(temp_magnets_dir)
        manager1.add("hash_one")
        manager1.add("hash_two")

        # Create new instance - should load from disk
        manager2 = HistoryManager(temp_magnets_dir)
        assert manager2.exists("hash_one") is True
        assert manager2.exists("hash_two") is True
        assert manager2.exists("hash_three") is False

    def test_no_duplicates_in_set(self, temp_magnets_dir):
        """Adding same hash twice should not create duplicates in set."""
        manager = HistoryManager(temp_magnets_dir)
        manager.add("same_hash")
        manager.add("same_hash")

        # Set should only have one entry
        assert list(manager.seen).count("same_hash") == 1

    def test_load_handles_missing_file(self, temp_magnets_dir):
        """Manager should handle missing history file gracefully."""
        manager = HistoryManager(temp_magnets_dir)
        # File doesn't exist yet, should not raise
        manager.load()
        assert len(manager.seen) == 0

    def test_custom_filename(self, temp_magnets_dir):
        """Manager should accept custom history filename."""
        manager = HistoryManager(temp_magnets_dir, filename="custom.log")
        assert manager.filepath.endswith("custom.log")
