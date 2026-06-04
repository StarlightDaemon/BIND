"""Tests for the metrics dashboard (T3)."""

HASH_A = "a" * 40
HASH_B = "b" * 40


class TestStatsWindowKeys:
    def test_stats_returns_last_7_days_key(self, fresh_store):
        s = fresh_store.stats()
        assert "last_7_days" in s

    def test_stats_returns_last_30_days_key(self, fresh_store):
        s = fresh_store.stats()
        assert "last_30_days" in s

    def test_stats_empty_windows_are_zero(self, fresh_store):
        s = fresh_store.stats()
        assert s["last_7_days"] == 0
        assert s["last_30_days"] == 0

    def test_stats_today_included_in_7_day_window(self, fresh_store):
        from datetime import datetime

        today = datetime.now().strftime("%Y-%m-%d")
        fresh_store.add_magnet(HASH_A, "Today Book", today)
        s = fresh_store.stats()
        assert s["last_7_days"] == 1
        assert s["last_30_days"] == 1

    def test_stats_old_record_excluded_from_windows(self, fresh_store):
        fresh_store.add_magnet(HASH_A, "Old Book", "2020-01-01")
        s = fresh_store.stats()
        assert s["last_7_days"] == 0
        assert s["last_30_days"] == 0

    def test_stats_existing_keys_still_present(self, fresh_store):
        s = fresh_store.stats()
        assert "total" in s
        assert "today" in s
        assert "last_date" in s


class TestRecordScrapeRun:
    def test_record_inserts_one_row(self, fresh_store):
        fresh_store.record_scrape_run("success", 5, 1.23)
        count = fresh_store._conn.execute("SELECT COUNT(*) FROM scrape_runs").fetchone()[0]
        assert count == 1

    def test_record_stores_correct_values(self, fresh_store):
        fresh_store.record_scrape_run("success", 7, 2.5)
        row = fresh_store._conn.execute(
            "SELECT result, items_new, duration_s FROM scrape_runs LIMIT 1"
        ).fetchone()
        assert row[0] == "success"
        assert row[1] == 7
        assert abs(row[2] - 2.5) < 0.001

    def test_record_failure_result(self, fresh_store):
        fresh_store.record_scrape_run("failure", 0, 0.1)
        row = fresh_store._conn.execute("SELECT result FROM scrape_runs").fetchone()
        assert row[0] == "failure"

    def test_record_empty_result(self, fresh_store):
        fresh_store.record_scrape_run("empty", 0, 3.0)
        row = fresh_store._conn.execute("SELECT result FROM scrape_runs").fetchone()
        assert row[0] == "empty"

    def test_multiple_runs_all_stored(self, fresh_store):
        fresh_store.record_scrape_run("success", 1, 1.0)
        fresh_store.record_scrape_run("empty", 0, 0.5)
        fresh_store.record_scrape_run("failure", 0, 0.2)
        count = fresh_store._conn.execute("SELECT COUNT(*) FROM scrape_runs").fetchone()[0]
        assert count == 3

    def test_run_at_is_populated(self, fresh_store):
        fresh_store.record_scrape_run("success", 1, 0.9)
        row = fresh_store._conn.execute("SELECT run_at FROM scrape_runs").fetchone()
        assert row[0] is not None and len(row[0]) > 0


class TestMetricsRoute:
    def test_metrics_returns_200(self, client):
        response = client.get("/api/metrics")
        assert response.status_code == 200

    def test_metrics_returns_json(self, client):
        assert client.get("/api/metrics").is_json

    def test_metrics_contains_stats(self, client):
        data = client.get("/api/metrics").get_json()
        assert "stats" in data
        assert "last_7_days" in data["stats"]
        assert "last_30_days" in data["stats"]

    def test_metrics_empty_runs_shows_no_runs_message(self, client):
        data = client.get("/api/metrics").get_json()
        assert data["runs"] == []
        assert data["success_rate"] is None

    def test_metrics_shows_run_history(self, client, fresh_store):
        fresh_store.record_scrape_run("success", 3, 1.5)
        data = client.get("/api/metrics").get_json()
        assert any(r["result"] == "success" for r in data["runs"])

    def test_metrics_shows_success_rate(self, client, fresh_store):
        fresh_store.record_scrape_run("success", 5, 1.0)
        fresh_store.record_scrape_run("empty", 0, 0.5)
        data = client.get("/api/metrics").get_json()
        assert data["success_rate"] == 50
