"""Tests for the daemon container health check (src/healthcheck.py)."""

from datetime import datetime, timedelta, timezone

from src.core.storage import MagnetStore
from src.healthcheck import check


def _beat(store, state, age_s):
    store.beat(state, 60)
    beat_at = (datetime.now(timezone.utc) - timedelta(seconds=age_s)).isoformat()
    store._conn.execute("UPDATE daemon_heartbeat SET beat_at = ? WHERE id = 1", (beat_at,))


def test_fresh_heartbeat_exit_0(tmp_path):
    db = str(tmp_path / "hc.db")
    store = MagnetStore(db)
    _beat(store, "idle", 5)
    store.close()
    assert check(db) == 0


def test_disabled_state_exit_0(tmp_path):
    db = str(tmp_path / "hc.db")
    store = MagnetStore(db)
    _beat(store, "disabled", 99999)  # age irrelevant when disabled
    store.close()
    assert check(db) == 0


def test_stale_heartbeat_exit_1(tmp_path):
    db = str(tmp_path / "hc.db")
    store = MagnetStore(db)
    _beat(store, "idle", 200)
    store.close()
    assert check(db) == 1


def test_no_heartbeat_row_exit_1(tmp_path):
    db = str(tmp_path / "hc.db")
    store = MagnetStore(db)  # table exists, no beat written
    store.close()
    assert check(db) == 1


def test_no_database_exit_1(tmp_path):
    assert check(str(tmp_path / "does-not-exist.db")) == 1
