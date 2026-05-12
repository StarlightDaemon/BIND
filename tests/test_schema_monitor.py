"""Tests for SchemaHealthMonitor parse-rate drift detection."""

import logging
from datetime import datetime, timedelta, timezone

import pytest

from src.core.schema_monitor import ParseAttempt, SchemaHealthMonitor


class TestSchemaHealthMonitor:
    def test_initial_state_is_empty(self):
        monitor = SchemaHealthMonitor()
        assert len(monitor._attempts) == 0

    def test_record_adds_attempt(self):
        monitor = SchemaHealthMonitor()
        monitor.record("http://example.com", "td_exact", True)
        assert len(monitor._attempts) == 1
        assert monitor._attempts[0].success is True
        assert monitor._attempts[0].strategy_used == "td_exact"
        assert monitor._attempts[0].url == "http://example.com"

    def test_no_alert_below_min_sample_size(self, caplog):
        monitor = SchemaHealthMonitor()
        with caplog.at_level(logging.CRITICAL, logger="SchemaMonitor"):
            for i in range(SchemaHealthMonitor.MIN_SAMPLE_SIZE - 1):
                monitor.record(f"http://example.com/{i}", "td_exact", False)
        assert "SCHEMA_DRIFT_DETECTED" not in caplog.text

    def test_drift_detected_when_all_fail(self, caplog):
        monitor = SchemaHealthMonitor()
        with caplog.at_level(logging.CRITICAL, logger="SchemaMonitor"):
            for i in range(SchemaHealthMonitor.MIN_SAMPLE_SIZE):
                monitor.record(f"http://example.com/{i}", "td_exact", False)
        assert "SCHEMA_DRIFT_DETECTED" in caplog.text

    def test_no_drift_when_success_rate_above_threshold(self, caplog):
        monitor = SchemaHealthMonitor()
        with caplog.at_level(logging.CRITICAL, logger="SchemaMonitor"):
            for i in range(SchemaHealthMonitor.MIN_SAMPLE_SIZE):
                monitor.record(f"http://example.com/{i}", "td_exact", True)
        assert "SCHEMA_DRIFT_DETECTED" not in caplog.text

    def test_evicts_entries_outside_window(self):
        monitor = SchemaHealthMonitor()
        old = ParseAttempt(
            timestamp=datetime.now(timezone.utc) - timedelta(minutes=31),
            url="http://example.com/old",
            strategy_used="td_exact",
            success=True,
        )
        monitor._attempts.append(old)
        monitor.record("http://example.com/new", "td_exact", True)
        urls = [a.url for a in monitor._attempts]
        assert "http://example.com/old" not in urls
        assert "http://example.com/new" in urls

    def test_record_with_none_strategy(self):
        monitor = SchemaHealthMonitor()
        monitor.record("http://example.com", None, False)
        assert monitor._attempts[0].strategy_used is None
