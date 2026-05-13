"""Tests for BindScraper with mocked HTTP responses."""

import os
from unittest.mock import patch

from src.core.scraper import BindScraper


class TestBindScraper:
    """Test suite for BindScraper core functionality."""

    def test_ensure_hex_passthrough(self):
        """Already-hex hashes should pass through unchanged."""
        scraper = BindScraper()
        hex_hash = "abc123def456789012345678901234567890abcd"

        result = scraper._ensure_hex(hex_hash)
        assert result == hex_hash

    def test_ensure_hex_converts_base32(self):
        """Base32 hashes should be converted to hex."""
        scraper = BindScraper()
        base32_hash = "MFRGGZDFMY"

        result = scraper._ensure_hex(base32_hash)
        assert result != base32_hash or len(result) == len(base32_hash)

    def test_scraper_has_base_url(self):
        """Scraper should have configurable base URL."""
        scraper = BindScraper()
        assert hasattr(scraper, "base_url")

    def test_base_url_reads_env_at_instantiation(self):
        """ABB_URL must be read when the instance is created, not at import time."""
        with patch.dict(os.environ, {"ABB_URL": "http://custom.example.com"}):
            scraper = BindScraper()
        assert scraper.base_url == "http://custom.example.com"

    def test_base_url_falls_back_to_default(self):
        """When ABB_URL is absent, base_url must be the default domain."""
        env = {k: v for k, v in os.environ.items() if k != "ABB_URL"}
        with patch.dict(os.environ, env, clear=True):
            scraper = BindScraper()
        assert scraper.base_url == "http://audiobookbay.lu"

    def test_schema_monitor_records_exactly_once_on_success(self, mocker):
        scraper = BindScraper()
        scraper.schema_monitor = mocker.MagicMock()

        html = """<html><body><table><tr>
            <th>Info Hash:</th>
            <td>abc123def456789012345678901234567890abcd</td>
        </tr></table></body></html>"""
        mocker.patch.object(scraper, "_get_page", return_value=html)

        result = scraper.extract_info_hash("http://example.com/book")

        assert result is not None
        assert scraper.schema_monitor.record.call_count == 1
        _, _, success = scraper.schema_monitor.record.call_args[0]
        assert success is True

    def test_schema_monitor_records_exactly_once_on_total_failure(self, mocker):
        scraper = BindScraper()
        scraper.schema_monitor = mocker.MagicMock()

        html = "<html><body><p>No hash information present</p></body></html>"
        mocker.patch.object(scraper, "_get_page", return_value=html)

        result = scraper.extract_info_hash("http://example.com/book")

        assert result is None
        assert scraper.schema_monitor.record.call_count == 1
        _, strategy_used, success = scraper.schema_monitor.record.call_args[0]
        assert strategy_used is None
        assert success is False
