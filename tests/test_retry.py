"""Tests for RetryEngine backoff and classification logic."""

from unittest.mock import MagicMock, patch

from src.core.retry import RetryConfig, RetryEngine


class TestRetryEngineSuccess:
    def test_returns_result_on_first_success(self):
        engine = RetryEngine()
        config = RetryConfig(max_attempts=3)
        fn = MagicMock(return_value="ok")
        assert engine.execute(fn, config, "test") == "ok"
        fn.assert_called_once()

    def test_returns_result_on_second_attempt(self):
        engine = RetryEngine()
        config = RetryConfig(max_attempts=3, base_delay=0)
        exc = _make_exc(500)
        fn = MagicMock(side_effect=[exc, "ok"])
        with patch("time.sleep"):
            result = engine.execute(fn, config, "test")
        assert result == "ok"
        assert fn.call_count == 2


class TestRetryEngineSleepBehaviour:
    """Verify sleep is called on non-final attempts and skipped on the last."""

    def test_retryable_status_no_sleep_on_last_attempt(self):
        engine = RetryEngine()
        config = RetryConfig(max_attempts=2, base_delay=1.0)
        exc = _make_exc(503)
        fn = MagicMock(side_effect=[exc, exc])
        with patch("time.sleep") as mock_sleep:
            engine.execute(fn, config, "test")
        # Only attempt 1 should sleep; attempt 2 is the last — no sleep
        assert mock_sleep.call_count == 1

    def test_429_no_sleep_on_last_attempt(self):
        engine = RetryEngine()
        config = RetryConfig(max_attempts=2, base_delay=1.0)
        exc = _make_exc(429)
        fn = MagicMock(side_effect=[exc, exc])
        with patch("time.sleep") as mock_sleep:
            engine.execute(fn, config, "test")
        assert mock_sleep.call_count == 1

    def test_transient_error_no_sleep_on_last_attempt(self):
        engine = RetryEngine()
        config = RetryConfig(max_attempts=2, base_delay=1.0)
        fn = MagicMock(side_effect=[ConnectionError(), ConnectionError()])
        with patch("time.sleep") as mock_sleep:
            engine.execute(fn, config, "test")
        assert mock_sleep.call_count == 1

    def test_retryable_status_sleeps_on_intermediate_attempts(self):
        engine = RetryEngine()
        config = RetryConfig(max_attempts=3, base_delay=1.0)
        exc = _make_exc(503)
        fn = MagicMock(side_effect=[exc, exc, exc])
        with patch("time.sleep") as mock_sleep:
            engine.execute(fn, config, "test")
        # Attempts 1 and 2 sleep; attempt 3 is last — no sleep
        assert mock_sleep.call_count == 2


class TestRetryEngineClassification:
    def test_permanent_http_returns_none_immediately(self):
        engine = RetryEngine()
        config = RetryConfig(max_attempts=3)
        exc = _make_exc(404)
        fn = MagicMock(side_effect=exc)
        with patch("time.sleep") as mock_sleep:
            result = engine.execute(fn, config, "test")
        assert result is None
        fn.assert_called_once()
        mock_sleep.assert_not_called()

    def test_non_retryable_exception_returns_none_immediately(self):
        engine = RetryEngine()
        config = RetryConfig(max_attempts=3)
        fn = MagicMock(side_effect=ValueError("bad"))
        with patch("time.sleep") as mock_sleep:
            result = engine.execute(fn, config, "test")
        assert result is None
        fn.assert_called_once()
        mock_sleep.assert_not_called()

    def test_exhausted_retryable_returns_none(self):
        engine = RetryEngine()
        config = RetryConfig(max_attempts=3, base_delay=0)
        exc = _make_exc(502)
        fn = MagicMock(side_effect=[exc, exc, exc])
        with patch("time.sleep"):
            result = engine.execute(fn, config, "test")
        assert result is None
        assert fn.call_count == 3


class TestRetryEngineRealTransientExceptions:
    """RES-2 regression: the transient-network branch must match the *real*
    exception types raised by curl_cffi and requests/cloudscraper, not just
    the Python builtins. These tests raise the actual library classes; against
    the pre-fix code (isinstance check on builtins only) they fail because the
    callable escalates immediately instead of retrying max_attempts times.
    """

    def test_requests_connection_error_is_retried(self):
        import requests.exceptions

        engine = RetryEngine()
        config = RetryConfig(max_attempts=3, base_delay=0)
        exc = requests.exceptions.ConnectionError("connection refused")
        fn = MagicMock(side_effect=[exc, exc, exc])
        with patch("time.sleep") as mock_sleep:
            result = engine.execute(fn, config, "cloudscraper")
        assert result is None
        assert fn.call_count == 3
        # Slept on attempts 1 and 2, not on the final attempt.
        assert mock_sleep.call_count == 2

    def test_requests_timeout_is_retried(self):
        import requests.exceptions

        engine = RetryEngine()
        config = RetryConfig(max_attempts=3, base_delay=0)
        exc = requests.exceptions.Timeout("read timed out")
        fn = MagicMock(side_effect=[exc, exc, exc])
        with patch("time.sleep") as mock_sleep:
            result = engine.execute(fn, config, "cloudscraper")
        assert result is None
        assert fn.call_count == 3
        assert mock_sleep.call_count == 2

    def test_curl_cffi_connection_error_is_retried(self):
        import curl_cffi.requests.exceptions

        engine = RetryEngine()
        config = RetryConfig(max_attempts=3, base_delay=0)
        # libcurl code 7 (connect refused) surfaces as this class; code 6
        # (DNS) is a subclass, so this covers both.
        exc = curl_cffi.requests.exceptions.ConnectionError("Failed to connect")
        fn = MagicMock(side_effect=[exc, exc, exc])
        with patch("time.sleep") as mock_sleep:
            result = engine.execute(fn, config, "curl_cffi")
        assert result is None
        assert fn.call_count == 3
        assert mock_sleep.call_count == 2

    def test_curl_cffi_timeout_is_retried(self):
        import curl_cffi.requests.exceptions

        engine = RetryEngine()
        config = RetryConfig(max_attempts=3, base_delay=0)
        # libcurl code 28 (operation timed out) surfaces as this class.
        exc = curl_cffi.requests.exceptions.Timeout("Operation timed out")
        fn = MagicMock(side_effect=[exc, exc, exc])
        with patch("time.sleep") as mock_sleep:
            result = engine.execute(fn, config, "curl_cffi")
        assert result is None
        assert fn.call_count == 3
        assert mock_sleep.call_count == 2

    def test_curl_cffi_dns_error_is_retried(self):
        """DNSError (libcurl code 6) subclasses curl_cffi's ConnectionError."""
        import curl_cffi.requests.exceptions

        engine = RetryEngine()
        config = RetryConfig(max_attempts=3, base_delay=0)
        exc = curl_cffi.requests.exceptions.DNSError("Could not resolve host")
        fn = MagicMock(side_effect=[exc, exc, exc])
        with patch("time.sleep") as mock_sleep:
            result = engine.execute(fn, config, "curl_cffi")
        assert result is None
        assert fn.call_count == 3
        assert mock_sleep.call_count == 2

    def test_http_error_with_response_escalates_immediately(self):
        """Ordering guard: requests.exceptions.HTTPError also passes the
        transient isinstance check loosely (it is an OSError), but it carries a
        .response, so the permanent-HTTP-status branch must win and escalate
        immediately with zero retries.
        """
        import requests.exceptions

        engine = RetryEngine()
        config = RetryConfig(max_attempts=3, base_delay=0)
        exc = requests.exceptions.HTTPError("404 Not Found")
        response = MagicMock()
        response.status_code = 404
        response.headers = MagicMock()
        response.headers.get = MagicMock(return_value=None)
        exc.response = response
        fn = MagicMock(side_effect=exc)
        with patch("time.sleep") as mock_sleep:
            result = engine.execute(fn, config, "cloudscraper")
        assert result is None
        fn.assert_called_once()
        mock_sleep.assert_not_called()

    def test_value_error_escalates_immediately(self):
        """Cloudflare-marker path: a genuinely foreign exception (ValueError,
        raised by egress_manager on a Cloudflare block) is not transient and
        must escalate immediately.
        """
        engine = RetryEngine()
        config = RetryConfig(max_attempts=3, base_delay=0)
        fn = MagicMock(side_effect=ValueError("Cloudflare block detected"))
        with patch("time.sleep") as mock_sleep:
            result = engine.execute(fn, config, "curl_cffi")
        assert result is None
        fn.assert_called_once()
        mock_sleep.assert_not_called()


def _make_exc(status: int) -> Exception:
    """Build a minimal exception with a .response.status_code attribute."""
    exc = Exception(f"HTTP {status}")
    response = MagicMock()
    response.status_code = status
    response.headers = MagicMock()
    response.headers.get = MagicMock(return_value=None)
    exc.response = response
    return exc
