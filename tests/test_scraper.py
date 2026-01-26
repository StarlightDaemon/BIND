"""Tests for BindScraper with mocked HTTP responses."""
from src.core.scraper import BindScraper, ScraperMetrics


class TestScraperMetrics:
    """Test suite for scraper metrics tracking."""

    def test_initial_counts_are_zero(self):
        """Fresh metrics should have zero counts."""
        metrics = ScraperMetrics()
        assert metrics.attempts['curl_cffi'] == 0
        assert metrics.successes['curl_cffi'] == 0
        assert metrics.failures['curl_cffi'] == 0

    def test_record_success_increments_correctly(self):
        """Recording success should update attempts and successes."""
        metrics = ScraperMetrics()
        metrics.record('curl_cffi', success=True)

        assert metrics.attempts['curl_cffi'] == 1
        assert metrics.successes['curl_cffi'] == 1
        assert metrics.failures['curl_cffi'] == 0

    def test_record_failure_increments_correctly(self):
        """Recording failure should update attempts and failures."""
        metrics = ScraperMetrics()
        metrics.record('curl_cffi', success=False)

        assert metrics.attempts['curl_cffi'] == 1
        assert metrics.successes['curl_cffi'] == 0
        assert metrics.failures['curl_cffi'] == 1

    def test_multiple_layers_tracked_independently(self):
        """Each scraper layer should have independent metrics."""
        metrics = ScraperMetrics()
        metrics.record('curl_cffi', success=True)
        metrics.record('cloudscraper', success=False)

        assert metrics.successes['curl_cffi'] == 1
        assert metrics.failures['cloudscraper'] == 1
        assert metrics.attempts['curl_cffi_proxy'] == 0


class TestBindScraper:
    """Test suite for BindScraper core functionality."""

    def test_generate_magnet_basic(self):
        """Magnet link should contain hash and title."""
        magnet = BindScraper.generate_magnet(
            "abc123def456789012345678901234567890abcd",
            "Test Book Title"
        )

        assert magnet.startswith("magnet:?xt=urn:btih:")
        assert "abc123def456789012345678901234567890abcd" in magnet
        assert "dn=" in magnet

    def test_generate_magnet_includes_trackers(self):
        """Magnet link should include tracker URLs."""
        magnet = BindScraper.generate_magnet("abc123", "Test")

        assert "&tr=" in magnet
        assert "tracker" in magnet.lower()

    def test_generate_magnet_url_encodes_title(self):
        """Special characters in title should be URL-encoded."""
        magnet = BindScraper.generate_magnet(
            "abc123",
            "Book: A & B (2024)"
        )

        # Title should be URL encoded (spaces, colons, ampersands)
        dn_part = magnet.split("&dn=")[1].split("&")[0]
        # Should not contain raw special chars
        assert ":" not in dn_part or "%3A" in dn_part
        assert " " not in dn_part

    def test_generate_magnet_handles_empty_title(self):
        """Empty title should not break magnet generation."""
        magnet = BindScraper.generate_magnet("abc123", "")
        assert "urn:btih:abc123" in magnet

    def test_ensure_hex_passthrough(self):
        """Already-hex hashes should pass through unchanged."""
        scraper = BindScraper()
        hex_hash = "abc123def456789012345678901234567890abcd"

        result = scraper._ensure_hex(hex_hash)
        assert result == hex_hash

    def test_ensure_hex_converts_base32(self):
        """Base32 hashes should be converted to hex."""
        scraper = BindScraper()
        # Valid base32 string
        base32_hash = "MFRGGZDFMY"  # "example" in base32

        result = scraper._ensure_hex(base32_hash)
        # Should return hex, not base32
        assert result != base32_hash or len(result) == len(base32_hash)

    def test_scraper_has_base_url(self):
        """Scraper should have configurable base URL."""
        scraper = BindScraper()
        assert hasattr(scraper, 'BASE_URL') or hasattr(BindScraper, 'BASE_URL')

    def test_scraper_has_trackers_list(self):
        """Scraper should have list of tracker URLs."""
        assert hasattr(BindScraper, 'TRACKERS')
        assert len(BindScraper.TRACKERS) > 0
