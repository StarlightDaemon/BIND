"""Tests for the generate_magnet utility function."""

from src.core.magnet import generate_magnet


class TestGenerateMagnet:
    def test_generate_magnet_basic(self):
        """Magnet link should contain hash and title."""
        magnet = generate_magnet(
            "abc123def456789012345678901234567890abcd", "Test Book Title", ["udp://tracker.com"]
        )

        assert magnet.startswith("magnet:?xt=urn:btih:")
        assert "abc123def456789012345678901234567890abcd" in magnet
        assert "dn=" in magnet

    def test_generate_magnet_includes_trackers(self):
        """Magnet link should include tracker URLs."""
        magnet = generate_magnet("abc123", "Test", ["udp://tracker.com"])

        assert "&tr=" in magnet
        assert "tracker" in magnet.lower()

    def test_generate_magnet_url_encodes_title(self):
        """Special characters in title should be URL-encoded."""
        magnet = generate_magnet("abc123", "Book: A & B (2024)", [])

        dn_part = magnet.split("&dn=")[1].split("&")[0]
        assert ":" not in dn_part or "%3A" in dn_part
        assert " " not in dn_part

    def test_generate_magnet_handles_empty_title(self):
        """Empty title should not break magnet generation."""
        magnet = generate_magnet("abc123", "", [])
        assert "urn:btih:abc123" in magnet
