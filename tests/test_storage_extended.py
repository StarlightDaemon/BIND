"""Extended real-database tests for MagnetStore (src/core/storage.py).

All tests use a real SQLite file via tmp_path — no mocks of sqlite3.
Covers: schema, add_magnet, has_hash, recent, search, stats,
record_scrape_run, and WAL probe.
"""

import sqlite3
from datetime import datetime

from src.core.storage import MagnetStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

HASH_A = "a" * 40
HASH_B = "b" * 40
HASH_C = "c" * 40
HASH_D = "d" * 40
HASH_E = "e" * 40

TODAY = datetime.now().strftime("%Y-%m-%d")


def _store(tmp_path, name: str = "test.db") -> MagnetStore:
    """Return a fresh MagnetStore on a real local SQLite file."""
    return MagnetStore(str(tmp_path / name))


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


class TestSchema:
    def test_both_tables_exist_after_init(self, tmp_path):
        """Both 'magnets' and 'scrape_runs' tables must be created on init."""
        store = _store(tmp_path)
        conn = sqlite3.connect(str(tmp_path / "test.db"))
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        conn.close()
        store.close()
        assert "magnets" in tables
        assert "scrape_runs" in tables

    def test_fts_virtual_table_exists(self, tmp_path):
        """The magnets_fts FTS5 virtual table should also be created."""
        store = _store(tmp_path)
        conn = sqlite3.connect(str(tmp_path / "test.db"))
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        conn.close()
        store.close()
        assert "magnets_fts" in tables


# ---------------------------------------------------------------------------
# add_magnet
# ---------------------------------------------------------------------------


class TestAddMagnet:
    def test_insert_increases_count_by_one(self, tmp_path):
        """Inserting one record increases COUNT(*) in magnets by exactly 1."""
        store = _store(tmp_path)
        store.add_magnet(HASH_A, "Book Alpha", "2024-01-01")
        conn = sqlite3.connect(str(tmp_path / "test.db"))
        count = conn.execute("SELECT COUNT(*) FROM magnets").fetchone()[0]
        conn.close()
        store.close()
        assert count == 1

    def test_duplicate_insert_does_not_raise(self, tmp_path):
        """Inserting the same info_hash twice must not raise any exception."""
        store = _store(tmp_path)
        store.add_magnet(HASH_A, "Book Alpha", "2024-01-01")
        store.add_magnet(HASH_A, "Book Alpha Duplicate", "2024-02-01")  # must not raise
        store.close()

    def test_duplicate_insert_does_not_create_extra_row(self, tmp_path):
        """Inserting the same info_hash twice must not create a duplicate row (idempotent)."""
        store = _store(tmp_path)
        store.add_magnet(HASH_A, "Book Alpha", "2024-01-01")
        store.add_magnet(HASH_A, "Book Alpha Again", "2024-01-02")
        conn = sqlite3.connect(str(tmp_path / "test.db"))
        count = conn.execute("SELECT COUNT(*) FROM magnets").fetchone()[0]
        conn.close()
        store.close()
        assert count == 1

    def test_insert_returns_true_for_new_record(self, tmp_path):
        """add_magnet returns True when a new row is actually inserted."""
        store = _store(tmp_path)
        result = store.add_magnet(HASH_A, "Book Alpha", "2024-01-01")
        store.close()
        assert result is True

    def test_insert_returns_false_for_duplicate(self, tmp_path):
        """add_magnet returns False when the info_hash already exists."""
        store = _store(tmp_path)
        store.add_magnet(HASH_A, "Book Alpha", "2024-01-01")
        result = store.add_magnet(HASH_A, "Book Alpha", "2024-01-01")
        store.close()
        assert result is False


# ---------------------------------------------------------------------------
# has_hash
# ---------------------------------------------------------------------------


class TestHasHash:
    def test_returns_true_for_added_hash(self, tmp_path):
        """has_hash returns True for a hash that was previously added."""
        store = _store(tmp_path)
        store.add_magnet(HASH_A, "Book Alpha", "2024-01-01")
        assert store.has_hash(HASH_A) is True
        store.close()

    def test_returns_false_for_missing_hash(self, tmp_path):
        """has_hash returns False for a hash that was never added."""
        store = _store(tmp_path)
        assert store.has_hash(HASH_A) is False
        store.close()

    def test_case_insensitive_lookup(self, tmp_path):
        """has_hash normalises to lowercase — uppercase query still hits."""
        store = _store(tmp_path)
        store.add_magnet(HASH_A.lower(), "Book Alpha", "2024-01-01")
        assert store.has_hash(HASH_A.upper()) is True
        store.close()


# ---------------------------------------------------------------------------
# recent
# ---------------------------------------------------------------------------


class TestRecent:
    def test_returns_at_most_n_rows(self, tmp_path):
        """recent(limit=N) returns at most N rows."""
        store = _store(tmp_path)
        for i in range(10):
            store.add_magnet("a" * 39 + str(i), f"Book {i}", "2024-01-01")
        rows = store.recent(limit=4)
        store.close()
        assert len(rows) == 4

    def test_five_rows_limit_three_returns_three(self, tmp_path):
        """With 5 rows, recent(limit=3) returns exactly 3 rows."""
        store = _store(tmp_path)
        for i in range(5):
            store.add_magnet("b" * 39 + str(i), f"Book {i}", "2024-01-0" + str(i + 1))
        rows = store.recent(limit=3)
        store.close()
        assert len(rows) == 3

    def test_rows_ordered_last_in_first_out(self, tmp_path):
        """recent() returns rows newest first (last inserted, first returned)."""
        store = _store(tmp_path)
        store.add_magnet(HASH_A, "Old Book", "2024-01-01")
        store.add_magnet(HASH_B, "New Book", "2024-06-01")
        rows = store.recent()
        store.close()
        assert rows[0]["title"] == "New Book"
        assert rows[1]["title"] == "Old Book"


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


class TestSearch:
    def test_matching_title_returns_record(self, tmp_path):
        """search() with a query matching the title returns that record."""
        store = _store(tmp_path)
        store.add_magnet(HASH_A, "Dune Unabridged", "2024-01-01")
        store.add_magnet(HASH_B, "Foundation Series", "2024-01-02")
        rows, total = store.search("Dune")
        store.close()
        assert total == 1
        assert rows[0]["title"] == "Dune Unabridged"

    def test_empty_string_query_returns_all(self, tmp_path):
        """search('') returns all records."""
        store = _store(tmp_path)
        store.add_magnet(HASH_A, "Book One", "2024-01-01")
        store.add_magnet(HASH_B, "Book Two", "2024-01-02")
        rows, total = store.search("")
        store.close()
        assert total == 2

    def test_none_query_returns_all(self, tmp_path):
        """search(None) returns all records."""
        store = _store(tmp_path)
        store.add_magnet(HASH_A, "Book One", "2024-01-01")
        store.add_magnet(HASH_B, "Book Two", "2024-01-02")
        _, total = store.search(None)
        store.close()
        assert total == 2

    def test_short_query_fallback(self, tmp_path):
        """Short queries (<3 chars) use LIKE fallback, still return results."""
        store = _store(tmp_path)
        store.add_magnet(HASH_A, "XY Chronicles", "2024-01-01")
        rows, total = store.search("XY")
        store.close()
        assert total == 1


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------


class TestStats:
    def test_today_count_after_inserting_today(self, tmp_path):
        """After inserting 3 records with collected_date=today, stats()['today'] == 3."""
        store = _store(tmp_path)
        store.add_magnet(HASH_A, "Book A", TODAY)
        store.add_magnet(HASH_B, "Book B", TODAY)
        store.add_magnet(HASH_C, "Book C", TODAY)
        s = store.stats()
        store.close()
        assert s["today"] == 3

    def test_stats_has_last_7_days_key(self, tmp_path):
        """stats() must include 'last_7_days' key as an integer."""
        store = _store(tmp_path)
        store.add_magnet(HASH_A, "Book A", TODAY)
        s = store.stats()
        store.close()
        assert "last_7_days" in s
        assert isinstance(s["last_7_days"], int)

    def test_stats_has_last_30_days_key(self, tmp_path):
        """stats() must include 'last_30_days' key as an integer."""
        store = _store(tmp_path)
        store.add_magnet(HASH_A, "Book A", TODAY)
        s = store.stats()
        store.close()
        assert "last_30_days" in s
        assert isinstance(s["last_30_days"], int)

    def test_today_included_in_last_7_days(self, tmp_path):
        """Records inserted today must be counted in last_7_days."""
        store = _store(tmp_path)
        store.add_magnet(HASH_A, "Book A", TODAY)
        s = store.stats()
        store.close()
        assert s["last_7_days"] >= 1

    def test_today_included_in_last_30_days(self, tmp_path):
        """Records inserted today must be counted in last_30_days."""
        store = _store(tmp_path)
        store.add_magnet(HASH_A, "Book A", TODAY)
        s = store.stats()
        store.close()
        assert s["last_30_days"] >= 1


# ---------------------------------------------------------------------------
# record_scrape_run
# ---------------------------------------------------------------------------


class TestRecordScrapeRun:
    def test_record_creates_one_row(self, tmp_path):
        """After one record_scrape_run call, COUNT(*) on scrape_runs is 1."""
        store = _store(tmp_path)
        store.record_scrape_run("success", 5, 1.23)
        conn = sqlite3.connect(str(tmp_path / "test.db"))
        count = conn.execute("SELECT COUNT(*) FROM scrape_runs").fetchone()[0]
        conn.close()
        store.close()
        assert count == 1

    def test_record_stores_correct_values(self, tmp_path):
        """The scrape_run row must have result='success' and items_new=5."""
        store = _store(tmp_path)
        store.record_scrape_run("success", 5, 1.23)
        conn = sqlite3.connect(str(tmp_path / "test.db"))
        row = conn.execute("SELECT result, items_new FROM scrape_runs LIMIT 1").fetchone()
        conn.close()
        store.close()
        assert row[0] == "success"
        assert row[1] == 5

    def test_multiple_runs_accumulate(self, tmp_path):
        """Multiple record_scrape_run calls each add a separate row."""
        store = _store(tmp_path)
        store.record_scrape_run("success", 3, 0.5)
        store.record_scrape_run("empty", 0, 0.1)
        store.record_scrape_run("failure", 0, 2.0)
        conn = sqlite3.connect(str(tmp_path / "test.db"))
        count = conn.execute("SELECT COUNT(*) FROM scrape_runs").fetchone()[0]
        conn.close()
        store.close()
        assert count == 3


# ---------------------------------------------------------------------------
# WAL probe
# ---------------------------------------------------------------------------


class TestWALProbe:
    def test_wal_probe_does_not_raise_on_local_path(self, tmp_path):
        """MagnetStore on a local tmp_path must not raise (WAL works locally)."""
        store = MagnetStore(str(tmp_path / "probe.db"))
        store.close()

    def test_store_is_functional_after_probe(self, tmp_path):
        """Store is fully operational after WAL probe completes."""
        store = MagnetStore(str(tmp_path / "probe2.db"))
        store.add_magnet(HASH_A, "Probed Book", TODAY)
        assert store.has_hash(HASH_A) is True
        store.close()
