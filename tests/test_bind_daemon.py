import concurrent.futures
import logging
import os
import signal
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner
from src.bind import check_disk_space, cli, run_job
from src.config_manager import LiveConfig


def _make_scraper(books=None, info_hash="aabbccdd" * 5):
    scraper = MagicMock()
    scraper.get_recent_books.return_value = (
        books if books is not None else [{"title": "Test Book", "link": "/audio-books/test/"}]
    )
    scraper.extract_info_hash.return_value = info_hash
    return scraper


def _make_tracker_manager():
    tm = MagicMock()
    tm.get_trackers.return_value = ["udp://tracker.example.com:1337"]
    return tm


class TestCheckDiskSpace:
    def test_returns_true_when_space_is_sufficient(self, tmp_path):
        with patch("shutil.disk_usage") as mock_usage:
            mock_usage.return_value = MagicMock(free=500 * 1024 * 1024)
            assert check_disk_space(str(tmp_path), required_mb=100) is True

    def test_returns_false_when_space_is_low(self, tmp_path):
        with patch("shutil.disk_usage") as mock_usage:
            mock_usage.return_value = MagicMock(free=50 * 1024 * 1024)
            assert check_disk_space(str(tmp_path), required_mb=100) is False

    def test_returns_true_on_oserror(self, tmp_path):
        with patch("shutil.disk_usage", side_effect=OSError("no stat")):
            assert check_disk_space(str(tmp_path)) is True

    def test_logs_warning_when_approaching_limit(self, tmp_path, caplog):
        import logging

        with patch("shutil.disk_usage") as mock_usage:
            mock_usage.return_value = MagicMock(free=150 * 1024 * 1024)
            with caplog.at_level(logging.WARNING, logger="BIND"):
                check_disk_space(str(tmp_path), required_mb=100)
        assert any("getting low" in r.message for r in caplog.records)


class TestRunJob:
    def test_saves_new_magnet_to_store(self, fresh_store):
        scraper = _make_scraper()
        run_job(str(fresh_store.db_path), scraper, fresh_store, _make_tracker_manager())
        assert fresh_store.stats()["total"] == 1

    def test_skips_duplicate_already_in_store(self, fresh_store):
        info_hash = "aabbccdd" * 5
        fresh_store.add_magnet(info_hash, "Test Book", "2024-01-01")
        scraper = _make_scraper(info_hash=info_hash)
        run_job(str(fresh_store.db_path), scraper, fresh_store, _make_tracker_manager())
        assert fresh_store.stats()["total"] == 1

    def test_hash_present_in_store_after_save(self, fresh_store):
        info_hash = "aabbccdd" * 5
        scraper = _make_scraper(info_hash=info_hash)
        run_job(str(fresh_store.db_path), scraper, fresh_store, _make_tracker_manager())
        assert fresh_store.has_hash(info_hash)

    def test_failed_hash_extraction_does_not_write(self, fresh_store):
        scraper = _make_scraper(info_hash=None)
        run_job(str(fresh_store.db_path), scraper, fresh_store, _make_tracker_manager())
        assert fresh_store.stats()["total"] == 0

    def test_empty_book_list_writes_nothing(self, fresh_store):
        scraper = _make_scraper(books=[])
        run_job(str(fresh_store.db_path), scraper, fresh_store, _make_tracker_manager())
        assert fresh_store.stats()["total"] == 0

    def test_returns_early_when_disk_space_low(self, fresh_store):
        scraper = _make_scraper()
        with patch("src.bind.check_disk_space", return_value=False):
            run_job(str(fresh_store.db_path), scraper, fresh_store, _make_tracker_manager())
        scraper.get_recent_books.assert_not_called()

    def test_multiple_books_all_saved(self, fresh_store):
        books = [{"title": "Book A", "link": "/a/"}, {"title": "Book B", "link": "/b/"}]
        hashes = ["aa" * 20, "bb" * 20]
        scraper = MagicMock()
        scraper.get_recent_books.return_value = books
        scraper.extract_info_hash.side_effect = hashes
        run_job(str(fresh_store.db_path), scraper, fresh_store, _make_tracker_manager())
        assert fresh_store.stats()["total"] == 2
        assert fresh_store.has_hash(hashes[0])
        assert fresh_store.has_hash(hashes[1])

    def test_store_exception_does_not_crash_job(self, fresh_store):
        scraper = _make_scraper()
        broken_store = MagicMock()
        broken_store.has_hash.return_value = False
        broken_store.add_magnet.side_effect = Exception("db error")
        broken_store.db_path = fresh_store.db_path
        # Should log error and continue, not raise
        run_job(str(fresh_store.db_path), scraper, broken_store, _make_tracker_manager())


class TestDaemonCommand:
    def test_permission_error_on_makedirs_exits_1(self, tmp_path):
        # Point LiveConfig at an empty tmp config so the cleared environment
        # cannot fall back to the repository's real config.env.
        with patch.dict("os.environ", {}, clear=True):
            os.environ["FLASK_SECRET_KEY"] = "testsecret"
            with (
                patch("src.bind.LiveConfig", lambda: LiveConfig(str(tmp_path / "config.env"))),
                patch("src.bind.BindScraper"),
                patch("src.bind.TrackerManager"),
            ):
                with patch("os.makedirs", side_effect=PermissionError):
                    result = CliRunner().invoke(
                        cli, ["daemon", "--db-path", "/no/permission/bind.db"]
                    )
        assert result.exit_code == 1

    def test_oserror_on_makedirs_exits_1(self, tmp_path):
        with patch.dict("os.environ", {}, clear=True):
            os.environ["FLASK_SECRET_KEY"] = "testsecret"
            with (
                patch("src.bind.LiveConfig", lambda: LiveConfig(str(tmp_path / "config.env"))),
                patch("src.bind.BindScraper"),
                patch("src.bind.TrackerManager"),
            ):
                with patch("os.makedirs", side_effect=OSError("disk full")):
                    result = CliRunner().invoke(cli, ["daemon", "--db-path", "/bad/path/bind.db"])
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# Helpers shared by the new daemon test classes below
# ---------------------------------------------------------------------------


def _make_daemon_mocks(probe_return="ok"):
    """Return (mock_executor, mock_future, mock_scraper, mock_store) for daemon tests."""
    mock_future = MagicMock()
    mock_future.done.return_value = True
    mock_future.result.return_value = 0

    mock_executor = MagicMock()
    mock_executor.submit.return_value = mock_future

    mock_scraper = MagicMock()
    mock_scraper.probe_target.return_value = probe_return
    mock_scraper.get_recent_books.return_value = []

    mock_store = MagicMock()
    mock_store.record_scrape_run.return_value = None

    return mock_executor, mock_future, mock_scraper, mock_store


# ---------------------------------------------------------------------------
# New test classes
# ---------------------------------------------------------------------------


class TestRunJobEdgeCases:
    def test_add_magnet_returns_false_counts_as_dupe(self, fresh_store):
        scraper = MagicMock()
        scraper.get_recent_books.return_value = [{"title": "Test Book", "link": "/test/"}]
        scraper.extract_info_hash.return_value = "aabbccdd" * 5

        with patch.object(fresh_store, "add_magnet", return_value=False):
            run_job(str(fresh_store.db_path), scraper, fresh_store, _make_tracker_manager())

        assert fresh_store.stats()["total"] == 0

    def test_saved_counter_is_updated_on_save(self, fresh_store):
        scraper = MagicMock()
        scraper.get_recent_books.return_value = [{"title": "Book A", "link": "/a/"}]
        scraper.extract_info_hash.return_value = "aa" * 20
        counter = [0]
        run_job(
            str(fresh_store.db_path),
            scraper,
            fresh_store,
            _make_tracker_manager(),
            _saved_counter=counter,
        )
        assert counter[0] == 1


class TestDaemonConfigLoading:
    # NOTE (Wave 5-B): the three tests that exercised seeding config.env into
    # os.environ ("Config mismatch", "Loaded N configuration values", and the
    # load-exception warning) were deleted — the daemon no longer seeds the
    # environment; it reads config.env live through LiveConfig (ARCH-2/SEC-2).

    def test_scraping_disabled_logs_waiting_message(self, tmp_path, monkeypatch, caplog):
        # An operator-exported SCRAPING_ENABLED=false is snapshotted by
        # LiveConfig at daemon start and wins over config.env.
        mock_executor, _, mock_scraper, mock_store = _make_daemon_mocks()
        monkeypatch.setenv("SCRAPING_ENABLED", "false")

        with (
            patch("src.bind.MagnetStore", return_value=mock_store),
            patch("src.bind.BindScraper", return_value=mock_scraper),
            patch("src.bind.TrackerManager"),
            patch("concurrent.futures.ThreadPoolExecutor", return_value=mock_executor),
            patch("src.bind.schedule"),
            patch("time.sleep", side_effect=SystemExit(0)),
        ):
            with caplog.at_level(logging.INFO, logger="BIND"):
                CliRunner().invoke(cli, ["daemon", "--db-path", str(tmp_path / "bind.db")])

        assert any("Scraping is disabled" in r.message for r in caplog.records)


class TestDaemonStartupFailures:
    def test_magnet_store_runtime_error_exits_1(self, tmp_path):
        with (
            patch("src.bind.MagnetStore", side_effect=RuntimeError("db locked")),
            patch("src.bind.BindScraper"),
            patch("src.bind.TrackerManager"),
        ):
            result = CliRunner().invoke(cli, ["daemon", "--db-path", str(tmp_path / "bind.db")])

        assert result.exit_code == 1


class TestDaemonSignalRegistration:
    def test_signal_handlers_registered_for_sigterm_and_sigint(self, tmp_path):
        mock_executor, _, mock_scraper, mock_store = _make_daemon_mocks()
        registered = {}

        def capture_signal(signum, handler):
            registered[signum] = handler

        with (
            patch("src.bind.MagnetStore", return_value=mock_store),
            patch("src.bind.BindScraper", return_value=mock_scraper),
            patch("src.bind.TrackerManager"),
            patch("concurrent.futures.ThreadPoolExecutor", return_value=mock_executor),
            patch("src.bind.schedule"),
            patch("signal.signal", side_effect=capture_signal),
            patch("time.sleep", side_effect=SystemExit(0)),
        ):
            CliRunner().invoke(cli, ["daemon", "--db-path", str(tmp_path / "bind.db")])

        assert signal.SIGTERM in registered
        assert signal.SIGINT in registered


class TestDaemonProbeWarning:
    def _run_with_probe(self, tmp_path, probe_return, caplog):
        mock_executor, _, mock_scraper, mock_store = _make_daemon_mocks(probe_return=probe_return)

        with (
            patch("src.bind.MagnetStore", return_value=mock_store),
            patch("src.bind.BindScraper", return_value=mock_scraper),
            patch("src.bind.TrackerManager"),
            patch("concurrent.futures.ThreadPoolExecutor", return_value=mock_executor),
            patch("src.bind.schedule"),
            patch("time.sleep", side_effect=SystemExit(0)),
        ):
            with caplog.at_level(logging.WARNING, logger="BIND"):
                CliRunner().invoke(cli, ["daemon", "--db-path", str(tmp_path / "bind.db")])

    def test_probe_unreachable_logs_warning(self, tmp_path, caplog):
        self._run_with_probe(tmp_path, "unreachable", caplog)
        assert any("unreachable" in r.message for r in caplog.records)

    def test_probe_wrong_content_logs_warning(self, tmp_path, caplog):
        self._run_with_probe(tmp_path, "wrong_content", caplog)
        assert any("wrong_content" in r.message for r in caplog.records)


class TestRunJobWithTimeout:
    def _invoke_capturing_rjwt(self, tmp_path, mock_executor, mock_scraper, mock_store):
        """Run daemon until time.sleep breaks the loop; return captured run_job_with_timeout."""
        captured = {}
        mock_sched = MagicMock()
        mock_sched.every.return_value.minutes.do.side_effect = (
            lambda fn: captured.update({"fn": fn}) or MagicMock()
        )

        with (
            patch("src.bind.MagnetStore", return_value=mock_store),
            patch("src.bind.BindScraper", return_value=mock_scraper),
            patch("src.bind.TrackerManager"),
            patch("concurrent.futures.ThreadPoolExecutor", return_value=mock_executor),
            patch("src.bind.schedule", mock_sched),
            patch("time.sleep", side_effect=SystemExit(0)),
        ):
            CliRunner().invoke(cli, ["daemon", "--db-path", str(tmp_path / "bind.db")])

        return captured.get("fn")

    def test_skips_run_when_previous_job_still_running(self, tmp_path, caplog):
        # First call at line 208 sets _last_future to a future that reports not-done.
        # Second call (via captured rjwt) should log the skip warning.
        future_not_done = MagicMock()
        future_not_done.done.return_value = False
        future_not_done.result.return_value = 0

        mock_executor = MagicMock()
        mock_executor.submit.return_value = future_not_done

        mock_scraper = MagicMock()
        mock_scraper.probe_target.return_value = "ok"
        mock_store = MagicMock()
        mock_store.record_scrape_run.return_value = None

        rjwt = self._invoke_capturing_rjwt(tmp_path, mock_executor, mock_scraper, mock_store)
        assert rjwt is not None

        with caplog.at_level(logging.WARNING, logger="BIND"):
            rjwt()

        assert any("Previous job is still running" in r.message for r in caplog.records)

    def test_records_scrape_run_on_timeout(self, tmp_path, caplog):
        future_timeout = MagicMock()
        future_timeout.done.return_value = True

        def _timeout_with_counter(*args, **kwargs):
            # Simulate the worker having saved 3 items before the timeout fires
            # by writing into the _saved_counter that submit() receives.
            counter = mock_executor.submit.call_args[0][5]
            counter[0] = 3
            raise concurrent.futures.TimeoutError()

        future_timeout.result.side_effect = _timeout_with_counter

        mock_executor = MagicMock()
        mock_executor.submit.return_value = future_timeout

        mock_scraper = MagicMock()
        mock_scraper.probe_target.return_value = "ok"
        mock_store = MagicMock()
        mock_store.record_scrape_run.return_value = None

        with caplog.at_level(logging.WARNING, logger="BIND"):
            self._invoke_capturing_rjwt(tmp_path, mock_executor, mock_scraper, mock_store)

        assert any("exceeded" in r.message for r in caplog.records)
        mock_store.record_scrape_run.assert_called_with("timeout", 3, pytest.approx(0, abs=5))

    def test_records_scrape_run_on_unexpected_exception(self, tmp_path, caplog):
        future_exc = MagicMock()
        future_exc.done.return_value = True
        future_exc.result.side_effect = ValueError("boom")

        mock_executor = MagicMock()
        mock_executor.submit.return_value = future_exc

        mock_scraper = MagicMock()
        mock_scraper.probe_target.return_value = "ok"
        mock_store = MagicMock()
        mock_store.record_scrape_run.return_value = None

        with caplog.at_level(logging.ERROR, logger="BIND"):
            self._invoke_capturing_rjwt(tmp_path, mock_executor, mock_scraper, mock_store)

        assert any("unexpected exception" in r.message for r in caplog.records)
