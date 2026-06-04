"""Tests for BindScraper.probe_target()."""

from unittest.mock import MagicMock

import pytest
from src.core.scraper import BindScraper


@pytest.fixture()
def scraper(mocker):
    s = BindScraper()
    s.egress._cffi_session = MagicMock()
    return s


def _mock_response(body: str) -> MagicMock:
    resp = MagicMock()
    resp.text = body
    return resp


class TestProbeTarget:
    def test_cloudflare_block(self, scraper):
        scraper.egress._cffi_session.get.return_value = _mock_response("Just a moment...")
        assert scraper.probe_target() == "cloudflare_block"

    def test_cloudflare_attention_required(self, scraper):
        scraper.egress._cffi_session.get.return_value = _mock_response(
            "<html>Attention Required</html>"
        )
        assert scraper.probe_target() == "cloudflare_block"

    def test_wrong_content(self, scraper):
        scraper.egress._cffi_session.get.return_value = _mock_response(
            "<html>some other site</html>"
        )
        assert scraper.probe_target() == "wrong_content"

    def test_unreachable_on_connection_error(self, scraper):
        scraper.egress._cffi_session.get.side_effect = ConnectionError("refused")
        assert scraper.probe_target() == "unreachable"

    def test_reachable(self, scraper):
        scraper.egress._cffi_session.get.return_value = _mock_response(
            "<html><title>AudioBookBay</title><body>audiobookbay content</body></html>"
        )
        assert scraper.probe_target() == "reachable"

    def test_unreachable_on_timeout(self, scraper):
        scraper.egress._cffi_session.get.side_effect = TimeoutError("timed out")
        assert scraper.probe_target() == "unreachable"

    def test_probe_does_not_affect_circuit_breaker(self, scraper):
        scraper.egress._cffi_session.get.side_effect = ConnectionError("refused")
        initial_failures = scraper.circuit_breaker.failures
        scraper.probe_target()
        assert scraper.circuit_breaker.failures == initial_failures
