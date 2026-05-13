import concurrent.futures
import logging
import os
import shutil
import signal
import sys
import time
from datetime import datetime
from typing import Any

import click
import schedule

from src.config_manager import ConfigManager
from src.core.magnet import generate_magnet
from src.core.scraper import BindScraper
from src.core.storage import MagnetStore
from src.core.tracker_manager import TrackerManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("bind.log", encoding="utf-8")],
)
logger = logging.getLogger("BIND")


def check_disk_space(path: str, required_mb: int = 100) -> bool:
    try:
        stat = shutil.disk_usage(path)
        free_mb = stat.free / (1024 * 1024)
        if free_mb < required_mb:
            logger.error(f"Low disk space: {free_mb:.1f}MB free (require {required_mb}MB)")
            return False
        elif free_mb < required_mb * 2:
            logger.warning(f"Disk space getting low: {free_mb:.1f}MB free")
        return True
    except OSError as e:
        logger.error(f"Could not check disk space: {e}")
        return True


def run_job(
    data_dir: str,
    scraper: BindScraper,
    store: MagnetStore,
    tracker_manager: TrackerManager,
) -> None:
    if not check_disk_space(data_dir, required_mb=100):
        logger.error("Insufficient disk space, skipping scrape job")
        return

    logger.info("Checking for new uploads...")
    books = scraper.get_recent_books()
    logger.info(f"Found {len(books)} recent books.")

    today = datetime.now().strftime("%Y-%m-%d")
    current_trackers = tracker_manager.get_trackers()

    successful_saves = 0
    failed_saves = 0
    skipped_dupes = 0

    for book in books:
        info_hash = scraper.extract_info_hash(book["link"])

        if not info_hash:
            logger.warning(f"Could not extract hash for: {book['title']}")
            failed_saves += 1
            continue

        if store.has_hash(info_hash):
            logger.debug(f"Skipping duplicate: {book['title']}")
            skipped_dupes += 1
            continue

        try:
            saved = store.add_magnet(info_hash, book["title"], today)
            if saved:
                # Log the magnet URI for operator reference
                magnet = generate_magnet(info_hash, book["title"], current_trackers)
                logger.info(f"✓ Saved ({successful_saves + 1}): {book['title'][:50]}...")
                logger.debug(f"  {magnet}")
                successful_saves += 1
            else:
                # Race condition: another process inserted between has_hash and add_magnet
                logger.debug(f"Skipping duplicate (race): {book['title']}")
                skipped_dupes += 1
        except Exception as e:
            logger.error(f"Failed to save '{book['title']}': {e}")
            failed_saves += 1

    if successful_saves > 0 or failed_saves > 0:
        logger.info(
            f"Job finished: {successful_saves} saved, {skipped_dupes} duplicates, {failed_saves} failed."
        )
    else:
        logger.info("Job finished: No new magnets found.")
    if failed_saves > 0:
        logger.warning(f"⚠️  {failed_saves} magnets could not be saved - check errors above")


@click.group()
def cli() -> None:
    """Book Indexing Network Daemon (BIND)"""
    pass


@cli.command()
@click.option("--interval", envvar="SCRAPE_INTERVAL", default=60, help="Check interval in minutes")
@click.option(
    "--db-path",
    envvar="BIND_DB_PATH",
    default="data/bind.db",
    help="Path to SQLite database",
)
def daemon(interval: int, db_path: str) -> None:
    """Run in daemon mode to auto-grab new torrents"""
    logger.info(f"Starting BIND Daemon (Interval: {interval}m)")
    logger.info(f"Database: {db_path}")

    try:
        config_mgr = ConfigManager()
        config = config_mgr.read_config()
        loaded_count = 0
        for key, value in config.items():
            if key not in os.environ:
                os.environ[key] = str(value)
                loaded_count += 1
            elif os.environ[key] != str(value):
                logger.debug(f"Config mismatch for {key}: Env={os.environ[key]} vs File={value}")
        logger.info(f"Loaded {loaded_count} configuration values from config.env")
    except Exception as e:
        logger.warning(f"Failed to load config.env: {e}")

    data_dir = os.path.dirname(os.path.abspath(db_path))
    try:
        os.makedirs(data_dir, exist_ok=True)
    except PermissionError:
        logger.critical(f"FATAL: No permission to create directory: {data_dir}")
        sys.exit(1)
    except OSError as e:
        logger.critical(f"FATAL: Cannot create data directory: {e}")
        sys.exit(1)

    try:
        store = MagnetStore(db_path)
    except RuntimeError as e:
        logger.critical(f"FATAL: {e}")
        sys.exit(1)

    scraper = BindScraper()
    tracker_manager = TrackerManager(data_dir)

    shutdown_requested = {"flag": False}

    def signal_handler(signum: int, frame: Any) -> None:
        signal_name = signal.Signals(signum).name
        logger.info(f"Received {signal_name}, will shutdown after current job completes...")
        shutdown_requested["flag"] = True

    logger.info("Registering signal handlers for graceful shutdown...")
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    JOB_TIMEOUT = int(os.getenv("BIND_JOB_TIMEOUT", "3600"))
    _job_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    _last_future: dict[str, Any] = {"future": None}

    def run_job_with_timeout() -> None:
        prev = _last_future["future"]
        if prev is not None and not prev.done():
            logger.warning(
                "⏰ Previous job is still running. "
                "Skipping this scheduled run to prevent queue buildup."
            )
            return
        future = _job_executor.submit(run_job, data_dir, scraper, store, tracker_manager)
        _last_future["future"] = future
        try:
            future.result(timeout=JOB_TIMEOUT)
        except concurrent.futures.TimeoutError:
            logger.warning(
                f"⏰ Job exceeded {JOB_TIMEOUT}s timeout. "
                "The next scheduled run will be skipped if this job has not completed."
            )
        except Exception as e:
            logger.error(f"Job raised unexpected exception: {e}")

    schedule.every(interval).minutes.do(run_job_with_timeout)

    run_job_with_timeout()

    logger.info("Daemon running. Press Ctrl+C to stop.")
    while not shutdown_requested["flag"]:
        schedule.run_pending()
        time.sleep(1)

    logger.info("Shutdown complete. Daemon stopped cleanly.")
    sys.exit(0)


if __name__ == "__main__":
    cli()
