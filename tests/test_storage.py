"""Tests for MagnetStore (src/core/storage.py)."""

import pytest
from src.core.storage import MagnetStore, _open, _upgrade_schema

HASH_A = "a" * 40
HASH_B = "b" * 40
HASH_C = "c" * 40


class TestAddAndHasHash:
    def test_add_new_magnet_returns_true(self, fresh_store):
        assert fresh_store.add_magnet(HASH_A, "Title A", "2024-01-01") is True

    def test_has_hash_returns_true_after_add(self, fresh_store):
        fresh_store.add_magnet(HASH_A, "Title A", "2024-01-01")
        assert fresh_store.has_hash(HASH_A) is True

    def test_has_hash_returns_false_for_unknown(self, fresh_store):
        assert fresh_store.has_hash(HASH_A) is False

    def test_duplicate_add_returns_false(self, fresh_store):
        fresh_store.add_magnet(HASH_A, "Title A", "2024-01-01")
        assert fresh_store.add_magnet(HASH_A, "Title A", "2024-01-01") is False

    def test_duplicate_does_not_create_extra_row(self, fresh_store):
        fresh_store.add_magnet(HASH_A, "Title A", "2024-01-01")
        fresh_store.add_magnet(HASH_A, "Title A duplicate", "2024-01-02")
        assert fresh_store.stats()["total"] == 1

    def test_hash_normalised_to_lowercase(self, fresh_store):
        fresh_store.add_magnet(HASH_A.upper(), "Title A", "2024-01-01")
        assert fresh_store.has_hash(HASH_A.lower()) is True

    def test_has_hash_case_insensitive(self, fresh_store):
        fresh_store.add_magnet(HASH_A, "Title A", "2024-01-01")
        assert fresh_store.has_hash(HASH_A.upper()) is True


class TestRecent:
    def test_recent_empty_store(self, fresh_store):
        assert fresh_store.recent() == []

    def test_recent_returns_most_recent_first(self, fresh_store):
        fresh_store.add_magnet(HASH_A, "Old Book", "2024-01-01")
        fresh_store.add_magnet(HASH_B, "New Book", "2024-06-01")
        rows = fresh_store.recent()
        assert rows[0]["title"] == "New Book"
        assert rows[1]["title"] == "Old Book"

    def test_recent_limit_respected(self, fresh_store):
        for i in range(10):
            fresh_store.add_magnet("a" * 39 + str(i), f"Book {i}", "2024-01-01")
        assert len(fresh_store.recent(limit=5)) == 5

    def test_recent_rows_have_expected_keys(self, fresh_store):
        fresh_store.add_magnet(HASH_A, "Title A", "2024-01-01")
        row = fresh_store.recent()[0]
        assert "info_hash" in row
        assert "title" in row
        assert "collected_date" in row

    def test_recent_same_date_ordered_by_insertion(self, fresh_store):
        fresh_store.add_magnet(HASH_A, "First", "2024-01-01")
        fresh_store.add_magnet(HASH_B, "Second", "2024-01-01")
        rows = fresh_store.recent()
        assert rows[0]["title"] == "Second"


class TestSearch:
    def _populate(self, store):
        store.add_magnet(HASH_A, "John Doe Unabridged", "2024-01-01")
        store.add_magnet(HASH_B, "Jane Smith Narrated", "2024-02-01")
        store.add_magnet(HASH_C, "Another John Story", "2024-03-01")

    def test_search_no_query_returns_all(self, fresh_store):
        self._populate(fresh_store)
        rows, total = fresh_store.search(None)
        assert total == 3

    def test_search_empty_string_returns_all(self, fresh_store):
        self._populate(fresh_store)
        _, total = fresh_store.search("")
        assert total == 3

    def test_search_matching_query(self, fresh_store):
        self._populate(fresh_store)
        rows, total = fresh_store.search("John")
        assert total == 2
        titles = {r["title"] for r in rows}
        assert "John Doe Unabridged" in titles
        assert "Another John Story" in titles

    def test_search_case_insensitive(self, fresh_store):
        self._populate(fresh_store)
        rows, total = fresh_store.search("john")
        assert total == 2

    def test_search_no_match_returns_empty(self, fresh_store):
        self._populate(fresh_store)
        rows, total = fresh_store.search("Zzzznotfound")
        assert total == 0
        assert rows == []

    def test_search_pagination(self, fresh_store):
        for i in range(10):
            fresh_store.add_magnet("a" * 39 + str(i), f"Book Alpha {i}", "2024-01-01")
        rows_p1, total = fresh_store.search("Alpha", page=1, per_page=4)
        rows_p2, _ = fresh_store.search("Alpha", page=2, per_page=4)
        assert total == 10
        assert len(rows_p1) == 4
        assert len(rows_p2) == 4
        titles_p1 = {r["title"] for r in rows_p1}
        titles_p2 = {r["title"] for r in rows_p2}
        assert titles_p1.isdisjoint(titles_p2)

    def test_short_query_still_works(self, fresh_store):
        # Queries < 3 chars fall back to LIKE scan
        fresh_store.add_magnet(HASH_A, "XY Book", "2024-01-01")
        rows, total = fresh_store.search("XY")
        assert total == 1

    def test_single_char_query(self, fresh_store):
        # Case-insensitive LIKE: 'Z' only appears in "Zephyr Book", not "Omega Book"
        fresh_store.add_magnet(HASH_A, "Zephyr Book", "2024-01-01")
        fresh_store.add_magnet(HASH_B, "Omega Book", "2024-01-01")
        rows, total = fresh_store.search("Z")
        assert total == 1
        assert rows[0]["title"] == "Zephyr Book"

    def test_search_returns_true_total_not_page_size(self, fresh_store):
        for i in range(60):
            fresh_store.add_magnet("a" * 39 + str(i), f"Book {i}", "2024-01-01")
        _, total = fresh_store.search(None, page=1, per_page=50)
        assert total == 60


class TestStats:
    def test_stats_empty_store(self, fresh_store):
        s = fresh_store.stats()
        assert s["total"] == 0
        assert s["today"] == 0
        assert s["last_date"] is None

    def test_stats_total_count(self, fresh_store):
        fresh_store.add_magnet(HASH_A, "Book A", "2024-01-01")
        fresh_store.add_magnet(HASH_B, "Book B", "2024-01-02")
        assert fresh_store.stats()["total"] == 2

    def test_stats_today_count(self, fresh_store):
        from datetime import datetime

        today = datetime.now().strftime("%Y-%m-%d")
        fresh_store.add_magnet(HASH_A, "Today Book", today)
        fresh_store.add_magnet(HASH_B, "Old Book", "2020-01-01")
        s = fresh_store.stats()
        assert s["today"] == 1
        assert s["total"] == 2

    def test_stats_last_date(self, fresh_store):
        fresh_store.add_magnet(HASH_A, "Old", "2023-01-01")
        fresh_store.add_magnet(HASH_B, "New", "2024-06-15")
        assert fresh_store.stats()["last_date"] == "2024-06-15"


class TestProbe:
    def test_bad_path_raises(self, tmp_path):
        with pytest.raises(Exception, match="unable to open"):
            MagnetStore("/nonexistent/path/that/cannot/be/created/bind.db")

    def test_fresh_store_on_valid_path(self, tmp_path):
        s = MagnetStore(str(tmp_path / "fresh.db"))
        assert s.stats()["total"] == 0
        s.close()


class TestUpgradeSchema:
    def _make_old_db(self, path: str) -> None:
        """Create a DB with the pre-timeout scrape_runs schema."""
        conn = _open(path)
        conn.execute(
            """CREATE TABLE IF NOT EXISTS scrape_runs (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                run_at     TEXT NOT NULL,
                result     TEXT NOT NULL CHECK(result IN ('success', 'failure', 'empty')),
                items_new  INTEGER NOT NULL DEFAULT 0,
                duration_s REAL    NOT NULL DEFAULT 0.0
            )"""
        )
        conn.execute(
            "INSERT INTO scrape_runs (run_at, result, items_new, duration_s)"
            " VALUES ('2024-01-01T00:00:00', 'success', 5, 1.0)"
        )
        conn.close()

    def test_upgrade_adds_timeout_variant(self, tmp_path):
        db = str(tmp_path / "old.db")
        self._make_old_db(db)
        conn = _open(db)
        _upgrade_schema(conn)
        # Should now accept 'timeout' without raising
        conn.execute(
            "INSERT INTO scrape_runs (run_at, result, items_new, duration_s)"
            " VALUES ('2024-01-02T00:00:00', 'timeout', 3, 120.0)"
        )
        rows = conn.execute("SELECT result FROM scrape_runs ORDER BY id").fetchall()
        assert [r[0] for r in rows] == ["success", "timeout"]
        conn.close()

    def test_upgrade_preserves_existing_rows(self, tmp_path):
        db = str(tmp_path / "old.db")
        self._make_old_db(db)
        conn = _open(db)
        _upgrade_schema(conn)
        count = conn.execute("SELECT COUNT(*) FROM scrape_runs").fetchone()[0]
        assert count == 1
        conn.close()

    def test_upgrade_is_idempotent(self, tmp_path):
        db = str(tmp_path / "fresh.db")
        s = MagnetStore(db)
        s.close()
        conn = _open(db)
        # Running upgrade on an already-upgraded schema should be a no-op
        _upgrade_schema(conn)
        conn.execute(
            "INSERT INTO scrape_runs (run_at, result, items_new, duration_s)"
            " VALUES ('2024-01-01T00:00:00', 'timeout', 0, 0.0)"
        )
        assert conn.execute("SELECT COUNT(*) FROM scrape_runs").fetchone()[0] == 1
        conn.close()
