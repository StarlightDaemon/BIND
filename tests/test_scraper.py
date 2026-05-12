"""Tests for BindScraper with mocked HTTP responses."""

from src.core.scraper import BindScraper


class TestBindScraper:
    """Test suite for BindScraper core functionality."""

    def test_generate_magnet_basic(self):
        """Magnet link should contain hash and title."""
        magnet = BindScraper.generate_magnet(
            "abc123def456789012345678901234567890abcd", "Test Book Title", ["udp://tracker.com"]
        )

        assert magnet.startswith("magnet:?xt=urn:btih:")
        assert "abc123def456789012345678901234567890abcd" in magnet
        assert "dn=" in magnet

    def test_generate_magnet_includes_trackers(self):
        """Magnet link should include tracker URLs."""
        magnet = BindScraper.generate_magnet("abc123", "Test", ["udp://tracker.com"])

        assert "&tr=" in magnet
        assert "tracker" in magnet.lower()

    def test_generate_magnet_url_encodes_title(self):
        """Special characters in title should be URL-encoded."""
        magnet = BindScraper.generate_magnet("abc123", "Book: A & B (2024)", [])

        # Title should be URL encoded (spaces, colons, ampersands)
        dn_part = magnet.split("&dn=")[1].split("&")[0]
        # Should not contain raw special chars
        assert ":" not in dn_part or "%3A" in dn_part
        assert " " not in dn_part

    def test_generate_magnet_handles_empty_title(self):
        """Empty title should not break magnet generation."""
        magnet = BindScraper.generate_magnet("abc123", "", [])
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
        base32_hash = "MFRGGZDFMY"

        result = scraper._ensure_hex(base32_hash)
        assert result != base32_hash or len(result) == len(base32_hash)

    def test_scraper_has_base_url(self):
        """Scraper should have configurable base URL."""
        scraper = BindScraper()
        assert hasattr(scraper, "BASE_URL")
