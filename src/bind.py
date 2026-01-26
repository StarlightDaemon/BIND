import fcntl
import glob
import logging
import os
import shutil
import signal
import sys
import time
from datetime import datetime

import click
import schedule

from src.config_manager import ConfigManager
from src.core.scraper import BindScraper

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("bind.log", encoding="utf-8")],
)
logger = logging.getLogger("BIND")


class HistoryManager:
    """Manages a persistent history of seen info hashes to prevent duplicates forever."""

    filepath: str
    seen: set[str]

    def __init__(self, output_dir: str, filename: str = "history.log") -> None:
        self.filepath = os.path.join(output_dir, filename)
        self.seen: set[str] = set()
        self.load()

    def load(self) -> None:
        """Load existing hashes from history file into memory."""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, encoding="utf-8") as f:
                    self.seen = {line.strip().lower() for line in f if line.strip()}
                logger.info(f"Loaded {len(self.seen)} hashes from history.")
            except Exception as e:
                logger.error(f"Failed to load history file: {e}")

    def exists(self, info_hash: str) -> bool:
        """Check if hash already exists."""
        return info_hash.lower() in self.seen

    def add(self, info_hash: str) -> None:
        """Add hash to memory and append to file."""
        clean_hash = info_hash.lower()
        if clean_hash not in self.seen:
            self.seen.add(clean_hash)
            try:
                with open(self.filepath, "a", encoding="utf-8") as f:
                    f.write(f"{clean_hash}\n")
            except Exception as e:
                logger.error(f"Failed to append to history file: {e}")


@click.group()
def cli():
    """Book Indexing Network Daemon (BIND)"""
    pass


@cli.command()
@click.option("--interval", envvar="SCRAPE_INTERVAL", default=60, help="Check interval in minutes")
@click.option(
    "--output-dir",
    envvar="MAGNETS_DIR",
    default="data/magnets",
    help="Directory to store magnet files",
)
def daemon(interval, output_dir):
    """Run in daemon mode to auto-grab new torrents"""
    logger.info(f"Starting BIND Daemon (Interval: {interval}m)")

    # [REMEDIATION RUNTIME-01] Legacy Fallback Support
    # If the canonical path is requested (default) but missing, and legacy exists, fallback.
    if (
        output_dir == "data/magnets"
        and not os.path.exists(output_dir)
        and os.path.exists("magnets")
    ):
        logger.warning(
            "Canonical directory 'data/magnets/' not found, but legacy 'magnets/' exists."
        )
        logger.warning(
            "FALLBACK: Using legacy 'magnets/' directory. Please migrate to 'data/magnets/'."
        )
        output_dir = "magnets"

    logger.info(f"Output directory: {output_dir}/")

    # [REMEDIATION CONF-01] Load config.env into environment
    # This ensures that manual runs or service restarts pick up UI changes
    try:
        config_mgr = ConfigManager()
        config = config_mgr.read_config()
        loaded_count = 0
        for key, value in config.items():
            # Only set if not already in env (systemd vars take precedence if set explicitly)
            # However, for the purpose of "UI Settings" being SOT for these values,
            # we want the file to win if the systemd var is just a default.
            # But standard behavior is Env Var > Config File.
            # Given the audit finding is "Daemon does not read config.env",
            # we simply ensure they are present.
            if key not in os.environ:
                os.environ[key] = str(value)
                loaded_count += 1
            # If the value in config.env differs from env, we might want to log it
            elif os.environ[key] != str(value):
                logger.debug(f"Config mismatch for {key}: Env={os.environ[key]} vs File={value}")

        logger.info(f"Loaded {loaded_count} configuration values from config.env")
    except Exception as e:
        logger.warning(f"Failed to load config.env: {e}")

    # Create output directory with error handling
    try:
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Output directory ready: {output_dir}/")
    except PermissionError:
        logger.critical(f"FATAL: No permission to create directory: {output_dir}")
        logger.critical("Daemon cannot run. Check directory permissions.")
        sys.exit(1)
    except OSError as e:
        logger.critical(f"FATAL: Cannot create output directory: {e}")
        logger.critical("Daemon cannot run. Exiting.")
        sys.exit(1)

    scraper = BindScraper()

    # Shutdown flag for graceful termination
    shutdown_requested = {"flag": False}

    # Define signal handler for graceful shutdown
    def signal_handler(signum, frame):
        """
        Handle shutdown signals gracefully.
        Sets a flag to stop after current job completes.
        Called when daemon receives SIGTERM (systemctl stop) or SIGINT (Ctrl+C)
        """
        signal_name = signal.Signals(signum).name
        logger.info(f"Received {signal_name}, will shutdown after current job completes...")
        shutdown_requested["flag"] = True

    # Register signal handlers for graceful shutdown
    logger.info("Registering signal handlers for graceful shutdown...")
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    def check_disk_space(path, required_mb=100):
        """
        Check if sufficient disk space is available.
        Returns True if >= required_mb MB free, False otherwise.
        """
        try:
            stat = shutil.disk_usage(path)
            free_mb = stat.free / (1024 * 1024)

            if free_mb < required_mb:
                logger.error(f"Low disk space: {free_mb:.1f}MB free (require {required_mb}MB)")
                return False
            elif free_mb < required_mb * 2:
                # Warning threshold: less than 2x required
                logger.warning(f"Disk space getting low: {free_mb:.1f}MB free")

            return True
        except OSError as e:
            logger.error(f"Could not check disk space: {e}")
            # Don't block on check failure
            return True

    def cleanup_old_files(path, days=90):
        """Delete files older than X days to prevent infinite accumulation"""
        try:
            cutoff = time.time() - (days * 86400)
            # Only look for magnets_*.txt files to be safe
            for f in glob.glob(os.path.join(path, "magnets_*.txt")):
                if os.path.getmtime(f) < cutoff:
                    try:
                        os.remove(f)
                        logger.info(f"Deleted old file (retention policy): {os.path.basename(f)}")
                    except OSError as e:
                        logger.error(f"Failed to delete old file {f}: {e}")
        except Exception as e:
            logger.error(f"Error during file cleanup: {e}")

    # Initialize Global History Manager
    history = HistoryManager(output_dir)

    def job():
        # Check disk space before starting job
        if not check_disk_space(output_dir, required_mb=100):
            logger.error("Insufficient disk space, skipping scrape job")
            return

        # Run cleanup policy (keep directory clean)
        cleanup_old_files(output_dir, days=90)

        logger.info("Checking for new uploads...")
        books = scraper.get_recent_books()
        logger.info(f"Found {len(books)} recent books.")

        # Date-based filename for daily rotation
        today = datetime.now().strftime("%Y-%m-%d")
        magnet_file = os.path.join(output_dir, f"magnets_{today}.txt")

        # Track save statistics
        successful_saves = 0
        failed_saves = 0
        skipped_dupes = 0

        for book in books:
            # Add politeness delay between requests
            # (scraper._get_page handles this now, but get_recent_books only calls it once for RSS)
            # We need to fetch detail page for each book

            # Note: extract_info_hash does the fetching + delay
            info_hash = scraper.extract_info_hash(book["link"])

            if info_hash:
                # Check Global History
                if history.exists(info_hash):
                    logger.debug(f"Skipping duplicate (history): {book['title']}")
                    skipped_dupes += 1
                    continue

                magnet = BindScraper.generate_magnet(info_hash, book["title"])

                # Save to date-based file with comprehensive error handling
                try:
                    with open(magnet_file, "a", encoding="utf-8") as f:
                        # Acquire exclusive lock to prevent RSS server reading partial writes
                        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                        try:
                            f.write(f"{magnet}\n")
                            # Add to global history immediately upon success
                            history.add(info_hash)
                        finally:
                            # Release lock (also auto-released on file close)
                            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                    logger.info(f"✓ Saved ({successful_saves + 1}): {book['title'][:50]}...")
                    successful_saves += 1

                except PermissionError:
                    logger.error(f"CRITICAL: Permission denied writing to {magnet_file}")
                    failed_saves += 1
                except OSError as e:
                    logger.error(f"CRITICAL: OS/IO error writing to {magnet_file}: {e}")
                    failed_saves += 1
            else:
                logger.warning(f"Could not extract hash for: {book['title']}")
                failed_saves += 1

        # Summary log
        if successful_saves > 0 or failed_saves > 0:
            logger.info(
                f"Job finished: {successful_saves} saved, {skipped_dupes} duplicates, {failed_saves} failed."
            )
        else:
            logger.info("Job finished: No new magnets found.")
        if failed_saves > 0:
            logger.warning(f"⚠️  {failed_saves} magnets could not be saved - check errors above")

        # Report scraping layer metrics (Phase 2)
        scraper.metrics.report()

    schedule.every(interval).minutes.do(job)

    # Run once immediately
    job()

    logger.info("Daemon running. Press Ctrl+C to stop.")
    while not shutdown_requested["flag"]:
        schedule.run_pending()
        time.sleep(1)

    logger.info("Shutdown complete. Daemon stopped cleanly.")
    sys.exit(0)


if __name__ == "__main__":
    cli()
