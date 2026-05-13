import os
from unittest.mock import MagicMock, patch

from click.testing import CliRunner
from src.bind import check_disk_space, cli, run_job


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
        with patch.dict("os.environ", {}, clear=True):
            os.environ["FLASK_SECRET_KEY"] = "testsecret"
            with (
                patch("src.bind.ConfigManager") as mock_cm,
                patch("src.bind.BindScraper"),
                patch("src.bind.TrackerManager"),
            ):
                mock_cm.return_value.read_config.return_value = {}
                with patch("os.makedirs", side_effect=PermissionError):
                    result = CliRunner().invoke(
                        cli, ["daemon", "--db-path", "/no/permission/bind.db"]
                    )
        assert result.exit_code == 1

    def test_oserror_on_makedirs_exits_1(self, tmp_path):
        with patch.dict("os.environ", {}, clear=True):
            os.environ["FLASK_SECRET_KEY"] = "testsecret"
            with (
                patch("src.bind.ConfigManager") as mock_cm,
                patch("src.bind.BindScraper"),
                patch("src.bind.TrackerManager"),
            ):
                mock_cm.return_value.read_config.return_value = {}
                with patch("os.makedirs", side_effect=OSError("disk full")):
                    result = CliRunner().invoke(cli, ["daemon", "--db-path", "/bad/path/bind.db"])
        assert result.exit_code == 1
