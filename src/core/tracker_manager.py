import fcntl
import json
import logging
import os
from pathlib import Path

logger = logging.getLogger("TrackerManager")

TrackerList = list[str]


class TrackerManager:
    """Manages persistent list of BitTorrent trackers."""

    DEFAULT_TRACKERS: TrackerList = [
        "udp://tracker.opentrackr.org:1337/announce",
        "udp://tracker.openbittorrent.com:80/announce",
        "udp://9.rarbg.to:2710/announce",
        "http://tracker.openbittorrent.com:80/announce",
        "udp://tracker.coppersurfer.tk:6969/announce",
    ]

    def __init__(self, magnets_dir: str) -> None:
        """
        Initialize TrackerManager.

        Args:
            magnets_dir: Directory where magnets are stored.
                         trackers.json will be in the parent directory.
        """
        self.path = Path(magnets_dir).parent / "trackers.json"
        logger.info(f"Resolved trackers.json path: {self.path}")

        # Ensure trackers.json exists with defaults if missing
        if not self.path.exists():
            logger.info("trackers.json missing. Initializing with defaults.")
            self.save(self.DEFAULT_TRACKERS)

    def load(self) -> TrackerList:
        """Load trackers from disk."""
        if not self.path.exists():
            return self.DEFAULT_TRACKERS

        try:
            with open(self.path, encoding="utf-8") as f:
                # Shared lock for concurrent reading
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    data = json.load(f)
                    if isinstance(data, list):
                        return self.normalize(data)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load trackers from {self.path}: {e}")

        return self.DEFAULT_TRACKERS

    def save(self, trackers: TrackerList) -> None:
        """
        Atomically save trackers to disk.
        Uses tmp + fsync + replace + lock.
        """
        normalized = self.normalize(trackers)
        tmp_path = self.path.with_suffix(".json.tmp")

        try:
            # Atomic write pattern
            with open(tmp_path, "w", encoding="utf-8") as f:
                # Exclusive lock during write
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    json.dump(normalized, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

            # Atomic replacement
            os.replace(tmp_path, self.path)
            logger.debug(f"Saved {len(normalized)} trackers to {self.path}")
        except OSError as e:
            logger.error(f"Failed to save trackers to {self.path}: {e}")
            if tmp_path.exists():
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            raise

    def get_trackers(self) -> TrackerList:
        """Get the current list of trackers."""
        return self.load()

    def set_trackers_from_text(self, text: str) -> None:
        """Parse, normalize, and save trackers from a raw text block (one per line)."""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        self.save(lines)

    def get_default_trackers(self) -> TrackerList:
        """Get the hardcoded default trackers."""
        return self.DEFAULT_TRACKERS

    def normalize(self, trackers: TrackerList) -> TrackerList:
        """
        Normalize trackers:
        1. Trim whitespace
        2. Filter by valid protocols (udp, http, https)
        3. Deduplicate case-insensitively (preserving first occurrence)
        """
        seen: set[str] = set()
        normalized: TrackerList = []

        valid_protocols = ("udp://", "http://", "https://")

        for tr in trackers:
            clean = tr.strip()
            if not clean:
                continue

            # Protocol validation
            if not clean.lower().startswith(valid_protocols):
                logger.warning(f"Rejecting invalid tracker protocol: {clean}")
                continue

            # Case-insensitive deduplication
            lowered = clean.lower()
            if lowered not in seen:
                seen.add(lowered)
                normalized.append(clean)

        return normalized
