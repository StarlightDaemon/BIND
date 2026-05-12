"""Tests for EgressManager, ProxyPool, and FetchExhausted."""

from unittest.mock import MagicMock, patch

import pytest
from src.core.egress_manager import EgressManager, FetchExhausted, ProxyPool


def _make_manager(proxy_list=None):
    """Build an EgressManager instance with all network components mocked."""
    manager = EgressManager.__new__(EgressManager)
    manager._proxy_pool = ProxyPool(proxy_list or [])
    manager._retry_engine = MagicMock()
    manager._cloudscraper = MagicMock()
    manager._cffi_session = MagicMock()
    return manager


class TestFetchExhausted:
    def test_message_contains_url(self):
        exc = FetchExhausted("http://example.com/page")
        assert "http://example.com/page" in str(exc)

    def test_url_attribute(self):
        exc = FetchExhausted("http://example.com/page")
        assert exc.url == "http://example.com/page"


class TestProxyPool:
    def test_get_next_returns_proxy(self):
        pool = ProxyPool(["http://proxy1.com"])
        assert pool.get_next() == "http://proxy1.com"

    def test_get_next_returns_none_when_empty(self):
        pool = ProxyPool([])
        assert pool.get_next() is None

    def test_round_robin_rotation(self):
        pool = ProxyPool(["http://a.com", "http://b.com"])
        assert pool.get_next() == "http://a.com"
        assert pool.get_next() == "http://b.com"
        assert pool.get_next() == "http://a.com"

    def test_mark_failed_removes_from_rotation(self):
        pool = ProxyPool(["http://a.com", "http://b.com"])
        pool.mark_failed("http://a.com")
        assert pool.get_next() == "http://b.com"
        assert pool.get_next() == "http://b.com"

    def test_get_next_returns_none_when_all_failed(self):
        pool = ProxyPool(["http://a.com"])
        pool.mark_failed("http://a.com")
        assert pool.get_next() is None

    def test_len_counts_healthy_proxies(self):
        pool = ProxyPool(["http://a.com", "http://b.com"])
        assert len(pool) == 2
        pool.mark_failed("http://a.com")
        assert len(pool) == 1


class TestEgressManagerFromEnv:
    def test_no_proxies_when_env_empty(self, monkeypatch):
        monkeypatch.delenv("BIND_PROXY", raising=False)
        monkeypatch.delenv("BIND_PROXIES", raising=False)
        with patch.object(EgressManager, "__init__", return_value=None) as mock_init:
            EgressManager.from_env()
            mock_init.assert_called_once_with(proxy_list=[])

    def test_reads_bind_proxy(self, monkeypatch):
        monkeypatch.setenv("BIND_PROXY", "http://proxy.com")
        monkeypatch.delenv("BIND_PROXIES", raising=False)
        with patch.object(EgressManager, "__init__", return_value=None) as mock_init:
            EgressManager.from_env()
            mock_init.assert_called_once_with(proxy_list=["http://proxy.com"])

    def test_reads_bind_proxies_comma_separated(self, monkeypatch):
        monkeypatch.setenv("BIND_PROXIES", "http://a.com,http://b.com")
        monkeypatch.delenv("BIND_PROXY", raising=False)
        with patch.object(EgressManager, "__init__", return_value=None) as mock_init:
            EgressManager.from_env()
            mock_init.assert_called_once_with(proxy_list=["http://a.com", "http://b.com"])

    def test_bind_proxies_takes_precedence(self, monkeypatch):
        monkeypatch.setenv("BIND_PROXIES", "http://new.com")
        monkeypatch.setenv("BIND_PROXY", "http://old.com")
        with patch.object(EgressManager, "__init__", return_value=None) as mock_init:
            EgressManager.from_env()
            mock_init.assert_called_once_with(proxy_list=["http://new.com"])


class TestEgressManagerFetch:
    def test_returns_html_on_first_layer_success(self):
        manager = _make_manager()
        manager._retry_engine.execute.return_value = "<html>ok</html>"
        result = manager.fetch("http://example.com")
        assert result == "<html>ok</html>"

    def test_raises_fetch_exhausted_when_all_layers_fail(self):
        manager = _make_manager()
        manager._retry_engine.execute.return_value = None
        with pytest.raises(FetchExhausted):
            manager.fetch("http://example.com")

    def test_proxy_layer_added_when_pool_has_proxy(self):
        manager = _make_manager(proxy_list=["http://proxy.com"])
        manager._retry_engine.execute.return_value = "<html>ok</html>"
        manager.fetch("http://example.com")
        assert manager._retry_engine.execute.call_count == 1

    def test_failed_proxy_marked_after_exhaustion(self):
        manager = _make_manager(proxy_list=["http://proxy.com"])
        # direct fails, proxy fails, cloudscraper succeeds
        manager._retry_engine.execute.side_effect = [None, None, "<html>ok</html>"]
        manager.fetch("http://example.com")
        assert "http://proxy.com" in manager._proxy_pool._failed
