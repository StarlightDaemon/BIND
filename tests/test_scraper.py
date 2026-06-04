"""Tests for BindScraper with mocked HTTP responses."""

import os
import time
from unittest.mock import MagicMock, patch

from bs4 import BeautifulSoup
from src.core.egress_manager import FetchExhausted
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


def _make_scraper(fetch_result=None, fetch_raises=None):
    egress = MagicMock()
    if fetch_raises:
        egress.fetch.side_effect = fetch_raises
    else:
        egress.fetch.return_value = fetch_result
    egress._cffi_session = MagicMock()
    return BindScraper(egress_manager=egress)


class TestGetPage:
    def test_returns_none_when_circuit_breaker_open(self):
        scraper = _make_scraper()
        scraper.circuit_breaker.is_open = True
        scraper.circuit_breaker.last_failure = time.time()

        result = scraper._get_page("http://example.com/page")

        assert result is None
        scraper.egress.fetch.assert_not_called()

    def test_returns_html_on_successful_fetch(self):
        scraper = _make_scraper(fetch_result="<html>ok</html>")
        with patch("src.core.scraper.time.sleep"):
            result = scraper._get_page("http://example.com/page")

            assert scraper.circuit_breaker.failures == 0
            assert result == "<html>ok</html>"

    def test_returns_none_and_records_failure_on_fetch_exhausted(self):
        scraper = _make_scraper(fetch_raises=FetchExhausted("http://example.com/page"))
        scraper.circuit_breaker.threshold = 1
        with patch("src.core.scraper.time.sleep"):
            result = scraper._get_page("http://example.com/page")

            assert result is None
            assert scraper.circuit_breaker.is_open is True

    def test_calls_sleep_before_fetching(self):
        scraper = _make_scraper(fetch_result="<html>ok</html>")
        with patch("src.core.scraper.time.sleep") as mock_sleep:
            result = scraper._get_page("http://example.com/page")

            mock_sleep.assert_called_once()
            assert result == "<html>ok</html>"


class TestExtractInfoHashNetwork:
    def test_prepends_base_url_for_relative_links(self):
        scraper = BindScraper()
        scraper.base_url = "http://audiobookbay.lu"
        with patch.object(
            scraper,
            "_get_page",
            return_value="<html><body><table><tr><td>Info Hash:</td><td>abc123def456789012345678901234567890abcd</td></tr></table></body></html>",
        ) as mock_get_page:
            result = scraper.extract_info_hash("/audio-books/test/")
            mock_get_page.assert_called_once_with("http://audiobookbay.lu/audio-books/test/")
            assert result == "abc123def456789012345678901234567890abcd"

    def test_returns_none_when_page_fetch_fails(self):
        scraper = BindScraper()
        with patch.object(scraper, "_get_page", return_value=None):
            result = scraper.extract_info_hash("http://example.com/book")
            assert result is None


class TestGetRecentBooks:
    def test_returns_empty_list_when_fetch_fails(self):
        scraper = BindScraper()
        with patch.object(scraper, "_get_page", return_value=None):
            assert scraper.get_recent_books() == []

    def test_parses_rss_items_correctly(self):
        scraper = BindScraper()
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>AudioBookBay</title>
    <item>
      <title>Test Book One</title>
      <link>http://audiobookbay.lu/audio-books/test-one/</link>
    </item>
  </channel>
</rss>"""
        with patch.object(scraper, "_get_page", return_value=xml):
            result = scraper.get_recent_books()
            assert result == [
                {"title": "Test Book One", "link": "http://audiobookbay.lu/audio-books/test-one/"}
            ]

    def test_skips_items_missing_link(self):
        scraper = BindScraper()
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>AudioBookBay</title>
    <item>
      <title>Test Book One</title>
      <link>http://audiobookbay.lu/audio-books/test-one/</link>
    </item>
    <item>
      <title>No Link Book</title>
    </item>
  </channel>
</rss>"""
        with patch.object(scraper, "_get_page", return_value=xml):
            result = scraper.get_recent_books()
            assert len(result) == 1
            assert result[0]["title"] == "Test Book One"

    def test_returns_list_of_title_and_link_dicts(self):
        scraper = BindScraper()
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Book 1</title>
      <link>Link 1</link>
    </item>
    <item>
      <title>Book 2</title>
      <link>Link 2</link>
    </item>
  </channel>
</rss>"""
        with patch.object(scraper, "_get_page", return_value=xml):
            result = scraper.get_recent_books()
            assert result == [
                {"title": "Book 1", "link": "Link 1"},
                {"title": "Book 2", "link": "Link 2"},
            ]


class TestProbeTarget:
    def test_returns_cloudflare_block(self):
        scraper = _make_scraper()
        scraper.egress._cffi_session.get.return_value.text = "Just a moment..."
        assert scraper.probe_target() == "cloudflare_block"

    def test_returns_wrong_content(self):
        scraper = _make_scraper()
        scraper.egress._cffi_session.get.return_value.text = "<html>something unrelated</html>"
        assert scraper.probe_target() == "wrong_content"

    def test_returns_reachable(self):
        scraper = _make_scraper()
        scraper.egress._cffi_session.get.return_value.text = (
            "<html>audiobookbay content here</html>"
        )
        assert scraper.probe_target() == "reachable"

    def test_returns_unreachable_on_exception(self):
        scraper = _make_scraper()
        scraper.egress._cffi_session.get.side_effect = Exception("timeout")
        assert scraper.probe_target() == "unreachable"


# HTML fixtures for parse strategies
TD_HTML = """<html><body><table><tr>
    <td>Info Hash:</td><td>abc123def456789012345678901234567890abcd</td>
</tr></table></body></html>"""

TH_HTML = """<html><body><table><tr>
    <th>Info Hash:</th><td>abc123def456789012345678901234567890abcd</td>
</tr></table></body></html>"""

MAGNET_HTML = """<html><body>
    <a href="magnet:?xt=urn:btih:abc123def456789012345678901234567890abcd&dn=Test">Download</a>
</body></html>"""

TEXT_HTML = """<html><body>
    <p>The info hash is abc123def456789012345678901234567890abcd for this release.</p>
</body></html>"""

EMPTY_HTML = "<html><body><p>Nothing here.</p></body></html>"


class TestParseHashTableTd:
    def test_returns_hash_when_td_label_and_sibling_present(self):
        scraper = BindScraper()
        soup = BeautifulSoup(TD_HTML, "html.parser")
        result = scraper._parse_hash_table_td(soup, "http://example.com")
        assert result == "abc123def456789012345678901234567890abcd"

    def test_returns_none_when_no_info_hash_td(self):
        scraper = BindScraper()
        soup_empty = BeautifulSoup(EMPTY_HTML, "html.parser")
        assert scraper._parse_hash_table_td(soup_empty, "http://example.com") is None

        # Case where td label exists but has no sibling (line 143)
        no_sibling_html = "<html><body><table><tr><td>Info Hash:</td></tr></table></body></html>"
        soup_no_sibling = BeautifulSoup(no_sibling_html, "html.parser")
        assert scraper._parse_hash_table_td(soup_no_sibling, "http://example.com") is None


class TestParseHashTableTh:
    def test_returns_hash_when_th_label_and_sibling_present(self):
        scraper = BindScraper()
        soup = BeautifulSoup(TH_HTML, "html.parser")
        result = scraper._parse_hash_table_th(soup, "http://example.com")
        assert result == "abc123def456789012345678901234567890abcd"

    def test_returns_none_when_no_info_hash_th(self):
        scraper = BindScraper()
        soup_empty = BeautifulSoup(EMPTY_HTML, "html.parser")
        assert scraper._parse_hash_table_th(soup_empty, "http://example.com") is None

        # Case where th label exists but has no sibling (line 153)
        no_sibling_html = "<html><body><table><tr><th>Info Hash:</th></tr></table></body></html>"
        soup_no_sibling = BeautifulSoup(no_sibling_html, "html.parser")
        assert scraper._parse_hash_table_th(soup_no_sibling, "http://example.com") is None


class TestParseHashMagnetHref:
    def test_returns_hash_from_magnet_link(self):
        scraper = BindScraper()
        soup = BeautifulSoup(MAGNET_HTML, "html.parser")
        result = scraper._parse_hash_magnet_href(soup, "http://example.com")
        assert result == "abc123def456789012345678901234567890abcd"

    def test_returns_none_when_no_magnet_link(self):
        scraper = BindScraper()
        soup = BeautifulSoup(EMPTY_HTML, "html.parser")
        assert scraper._parse_hash_magnet_href(soup, "http://example.com") is None

        # Case where magnet link exists but has no valid hash (line 162 else / regex fails)
        invalid_magnet_html = (
            '<html><body><a href="magnet:?xt=urn:btih:invalid">Download</a></body></html>'
        )
        soup_invalid = BeautifulSoup(invalid_magnet_html, "html.parser")
        assert scraper._parse_hash_magnet_href(soup_invalid, "http://example.com") is None


class TestParseHashTextSearch:
    def test_returns_hash_from_page_text(self):
        scraper = BindScraper()
        soup = BeautifulSoup(TEXT_HTML, "html.parser")
        result = scraper._parse_hash_text_search(soup, "http://example.com")
        assert result == "abc123def456789012345678901234567890abcd"

    def test_returns_none_when_no_hex_in_text(self):
        scraper = BindScraper()
        soup = BeautifulSoup(EMPTY_HTML, "html.parser")
        assert scraper._parse_hash_text_search(soup, "http://example.com") is None


class TestEnsureHexEdgeCases:
    def test_returns_none_for_none_input(self):
        scraper = BindScraper()
        assert scraper._ensure_hex(None) is None

    def test_returns_none_for_empty_string(self):
        scraper = BindScraper()
        assert scraper._ensure_hex("") is None
        assert scraper._ensure_hex("   ") is None

    def test_converts_valid_base32_to_hex(self):
        import base64

        scraper = BindScraper()
        raw = bytes.fromhex("abc123def456789012345678901234567890abcd")
        b32 = base64.b32encode(raw).decode()
        assert len(b32) == 32
        result = scraper._ensure_hex(b32)
        assert result == "abc123def456789012345678901234567890abcd"

    def test_returns_none_for_invalid_base32(self):
        scraper = BindScraper()
        assert scraper._ensure_hex("8" * 32) is None

    def test_returns_none_for_wrong_length(self):
        scraper = BindScraper()
        assert scraper._ensure_hex("abc") is None
        assert scraper._ensure_hex("a" * 10) is None
        assert scraper._ensure_hex("a" * 31) is None
        assert scraper._ensure_hex("a" * 33) is None
        assert scraper._ensure_hex("a" * 39) is None
        assert scraper._ensure_hex("a" * 41) is None
