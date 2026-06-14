import concurrent.futures
import logging
import logging.handlers
import os
import shutil
import signal
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import click
import schedule

from src.config_manager import LiveConfig
from src.core.magnet import generate_magnet
from src.core.scraper import BindScraper
from src.core.storage import MagnetStore
from src.core.tracker_manager import TrackerManager
from src.security import get_logs_dir

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.handlers.RotatingFileHandler(
            os.path.join(get_logs_dir(), "bind.log"),
            maxBytes=10 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        ),
    ],
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
    _saved_counter: list[int] | None = None,
) -> int:
    if not check_disk_space(data_dir, required_mb=100):
        logger.error("Insufficient disk space, skipping scrape job")
        return 0

    logger.info("Checking for new uploads...")
    books = scraper.get_recent_books()
    logger.info(f"Found {len(books)} recent books.")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
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
                if _saved_counter is not None:
                    _saved_counter[0] = successful_saves
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
    return successful_saves


@dataclass
class DaemonContext:
    """Mutable state shared between the daemon shell and loop_tick() (TEST-3)."""

    data_dir: str
    interval: int
    live_config: LiveConfig
    run_job: Callable[[], None]
    maybe_beat: Callable[..., None]
    # True iff the scrape job is currently on the scheduler. Reconciled against
    # the live SCRAPING_ENABLED value every tick by sync_scraping_schedule().
    scraping_enabled: bool = False

    @property
    def trigger_file(self) -> str:
        return os.path.join(self.data_dir, ".trigger")


def cleanup_stale_signal_files(data_dir: str) -> None:
    """Delete control files left over from a previous daemon run (startup only).

    - ``.enable-scraping`` (deprecated sentinel): a stale one — written while
      the daemon was already enabled, hence never consumed — used to re-enable
      scraping on a later restart *against* ``SCRAPING_ENABLED=false`` (ARCH-2).
      The daemon now reads config live and ignores the sentinel at runtime; the
      RSS server still writes it for one release for old daemons (COMPAT).
    - ``.trigger``: one left by a dead daemon caused a startup-run + trigger-run
      double scrape and 409-blocked manual scrapes forever (ARCH-3).
    """
    for name in (".enable-scraping", ".trigger"):
        path = os.path.join(data_dir, name)
        try:
            os.remove(path)
            logger.info("Removed stale %s left by a previous run.", name)
        except FileNotFoundError:
            pass
        except OSError as e:
            logger.warning("Could not remove stale %s: %s", name, e)


def sync_scraping_schedule(ctx: DaemonContext) -> bool:
    """Reconcile the scheduler with the live SCRAPING_ENABLED value (ARCH-2).

    Returns True when scraping was just enabled — the caller should run a job
    immediately. On a true→false transition the pending schedule is cleared:
    a running job finishes, no new ones start.
    """
    desired = ctx.live_config.get_bool("SCRAPING_ENABLED")
    if desired and not ctx.scraping_enabled:
        ctx.scraping_enabled = True
        schedule.every(ctx.interval).minutes.do(ctx.run_job)
        logger.info("SCRAPING_ENABLED=true — scrape job scheduled every %dm.", ctx.interval)
        return True
    if not desired and ctx.scraping_enabled:
        ctx.scraping_enabled = False
        schedule.clear()
        logger.info(
            "SCRAPING_ENABLED=false — schedule cleared; a running job will "
            "finish, no new ones start."
        )
    return False


def loop_tick(ctx: DaemonContext) -> None:
    """One iteration of the daemon main loop, extracted for testability (TEST-3)."""
    schedule.run_pending()
    run_now = sync_scraping_schedule(ctx)
    # Heartbeat every tick (Wave 5-A); a transition above changes the state
    # reported by _current_state(), which forces an immediate beat — so the UI
    # reflects an enable/disable before any (blocking) job below runs.
    ctx.maybe_beat()
    if run_now:
        ctx.run_job()
    if os.path.exists(ctx.trigger_file):
        try:
            os.remove(ctx.trigger_file)
        except OSError:
            pass
        logger.info("Manual trigger detected — running job immediately")
        ctx.run_job()


@click.group()
def cli() -> None:
    """Book Indexing Network Daemon (BIND)"""
    pass


@cli.command()
@click.option(
    "--interval",
    envvar="SCRAPE_INTERVAL",
    default=None,
    type=int,
    help="Check interval in minutes (default: SCRAPE_INTERVAL from env/config.env, else 60)",
)
@click.option(
    "--db-path",
    envvar="BIND_DB_PATH",
    default="data/bind.db",
    help="Path to SQLite database",
)
def daemon(interval: int | None, db_path: str) -> None:
    """Run in daemon mode to auto-grab new torrents"""
    # Single source of truth for managed config keys (ARCH-2/SEC-2): read live
    # from config.env per loop tick. config.env is NO LONGER seeded into
    # os.environ — only operator-exported variables live there now, and those
    # win permanently (LiveConfig snapshot).
    live_config = LiveConfig()

    if interval is None:
        # SCRAPE_INTERVAL is intentionally start-time-only: re-scheduling a
        # live interval change is out of scope (Wave 5-B). Restart to apply.
        interval = live_config.get_int("SCRAPE_INTERVAL")

    logger.info(f"Starting BIND Daemon (Interval: {interval}m)")
    logger.info(f"Database: {db_path}")

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
        # Read per job run so a Settings-page change applies without restart.
        job_timeout = live_config.get_int("BIND_JOB_TIMEOUT")
        t0 = time.monotonic()
        run_result = "failure"
        items_new = 0
        _saved_counter: list[int] = [0]
        future = _job_executor.submit(
            run_job, data_dir, scraper, store, tracker_manager, _saved_counter
        )
        _last_future["future"] = future
        try:
            new_count = future.result(timeout=job_timeout)
            items_new = new_count or 0
            run_result = "success" if items_new > 0 else "empty"
        except concurrent.futures.TimeoutError:
            items_new = _saved_counter[0]
            run_result = "timeout"
            logger.warning(
                f"⏰ Job exceeded {job_timeout}s timeout — "
                f"{items_new} item(s) saved before cutoff. "
                "The next scheduled run will be skipped if this job has not completed."
            )
        except Exception as e:
            logger.error(f"Job raised unexpected exception: {e}")
        finally:
            store.record_scrape_run(run_result, items_new, time.monotonic() - t0)

    probe_result = scraper.probe_target()
    if probe_result in ("unreachable", "wrong_content"):
        logger.warning(
            "Target domain probe returned '%s'. Check ABB_URL config. Current: %s",
            probe_result,
            scraper.base_url,
        )

    HEARTBEAT_INTERVAL_S = 30
    _last_beat: dict[str, Any] = {"at": 0.0, "state": None}

    def _current_state() -> str:
        if not ctx.scraping_enabled:
            return "disabled"
        fut = _last_future["future"]
        if fut is not None and not fut.done():
            return "scraping"
        return "idle"

    def _maybe_beat(force: bool = False) -> None:
        """Write a liveness heartbeat, throttled to HEARTBEAT_INTERVAL_S or on state change."""
        state = _current_state()
        now = time.monotonic()
        if force or state != _last_beat["state"] or now - _last_beat["at"] >= HEARTBEAT_INTERVAL_S:
            try:
                store.beat(state, interval)
            except Exception as e:  # heartbeat is best-effort, never fatal
                logger.debug(f"Heartbeat write failed: {e}")
            _last_beat["at"] = now
            _last_beat["state"] = state

    ctx = DaemonContext(
        data_dir=data_dir,
        interval=interval,
        live_config=live_config,
        run_job=run_job_with_timeout,
        maybe_beat=_maybe_beat,
    )

    # Kill any stale .enable-scraping / .trigger before the first scheduled run
    # (ARCH-2 stale-sentinel re-enable; ARCH-3 restart double-scrape).
    cleanup_stale_signal_files(data_dir)

    run_now = sync_scraping_schedule(ctx)
    _maybe_beat(force=True)  # flip UI status promptly, before the first (blocking) job
    if run_now:
        run_job_with_timeout()
    else:
        logger.info(
            "Scraping is disabled (SCRAPING_ENABLED=false). "
            "Enable it in Settings — applied within seconds, no restart needed."
        )

    logger.info("Daemon running. Press Ctrl+C to stop.")
    while not shutdown_requested["flag"]:  # pragma: no cover — shell only; body is loop_tick()
        loop_tick(ctx)  # pragma: no cover
        time.sleep(1)  # pragma: no cover

    logger.info("Shutdown complete. Daemon stopped cleanly.")
    sys.exit(0)


if __name__ == "__main__":
    cli()
