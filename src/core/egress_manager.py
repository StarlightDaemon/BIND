from __future__ import annotations

import logging
import os
from collections import deque
from typing import Any, cast

import cloudscraper

from src.core.retry import RetryConfig, RetryEngine

logger = logging.getLogger("EgressManager")

TIMEOUT = 30
MAX_RETRIES = 3


class FetchExhausted(Exception):
    """Raised when all egress paths (direct, proxy, cloudscraper) fail for a URL."""

    def __init__(self, url: str) -> None:
        super().__init__(f"All egress paths exhausted for: {url}")
        self.url = url


class ProxyPool:
    """Round-robin proxy rotation with health eviction."""

    def __init__(self, proxies: list[str]) -> None:
        self._pool: deque[str] = deque(proxies)
        self._failed: set[str] = set()

    def get_next(self) -> str | None:
        """Return the next healthy proxy, or None if none are available."""
        for _ in range(len(self._pool)):
            candidate = self._pool[0]
            self._pool.rotate(-1)
            if candidate not in self._failed:
                return candidate
        return None

    def mark_failed(self, proxy: str) -> None:
        """Evict a proxy from rotation permanently for this session."""
        self._failed.add(proxy)
        logger.warning(f"Proxy {proxy!r} marked unhealthy and removed from rotation")

    def __len__(self) -> int:
        return sum(1 for p in self._pool if p not in self._failed)


class EgressManager:
    """
    Manages all egress paths: direct curl_cffi, proxy curl_cffi, cloudscraper.
    Handles path selection, proxy rotation, and per-layer retry with backoff.
    Single responsibility: fetch HTML for a given URL.
    """

    def __init__(self, proxy_list: list[str] | None = None) -> None:
        from curl_cffi import requests as cffi_requests

        self._proxy_pool = ProxyPool(proxy_list or [])
        self._retry_engine = RetryEngine()
        self._cffi_session: Any = cffi_requests.Session(impersonate="chrome120")
        self._cloudscraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "desktop": True}
        )
        if proxy_list:
            logger.info(f"EgressManager: {len(proxy_list)} proxy(ies) configured")

    @classmethod
    def from_env(cls) -> EgressManager:
        """
        Factory: reads BIND_PROXIES (comma-separated list) with fallback to
        BIND_PROXY (single value). Both env vars are supported for backward
        compatibility.
        """
        raw = os.getenv("BIND_PROXIES") or os.getenv("BIND_PROXY") or ""
        proxies = [p.strip() for p in raw.split(",") if p.strip()]
        return cls(proxy_list=proxies)

    def fetch(self, url: str) -> str:
        """
        Attempt fetch via all available egress paths in order:
          1. curl_cffi direct
          2. curl_cffi + proxy (skipped if no healthy proxies in pool)
          3. cloudscraper

        Each path is retried up to MAX_RETRIES times with exponential backoff
        via RetryEngine before escalating to the next path.
        Raises FetchExhausted if every path on every retry fails.
        """
        config = RetryConfig(max_attempts=MAX_RETRIES)
        proxy = self._proxy_pool.get_next()

        layers: list[tuple[str, Any]] = [
            ("curl_cffi", lambda: self._fetch_curl_cffi(url, proxy=None)),
        ]
        if proxy:
            layers.append(("curl_cffi_proxy", lambda: self._fetch_curl_cffi(url, proxy=proxy)))
        layers.append(("cloudscraper", lambda: self._fetch_cloudscraper(url, proxy=proxy)))

        for layer_name, attempt_fn in layers:
            result = self._retry_engine.execute(attempt_fn, config, layer_name)
            if result is not None:
                logger.debug(f"✓ [{layer_name}] fetched {url}")
                return cast(str, result)
            logger.warning(f"[{layer_name}] all retries exhausted for {url}")
            if layer_name in ("curl_cffi_proxy", "cloudscraper") and proxy:
                self._proxy_pool.mark_failed(proxy)

        raise FetchExhausted(url)

    def _fetch_curl_cffi(self, url: str, proxy: str | None) -> str:
        response = self._cffi_session.get(url, proxy=proxy, timeout=TIMEOUT)
        cast(Any, response).raise_for_status()
        if "Just a moment..." in response.text or "Attention Required" in response.text:
            raise ValueError("Cloudflare block detected")
        return str(response.text)

    def _fetch_cloudscraper(self, url: str, proxy: str | None = None) -> str:
        kwargs: dict[str, Any] = {"timeout": TIMEOUT}
        if proxy:
            kwargs["proxies"] = {"http": proxy, "https": proxy}
        response = self._cloudscraper.get(url, **kwargs)
        response.raise_for_status()
        if "Just a moment..." in response.text or "Attention Required" in response.text:
            raise ValueError("Cloudflare block detected")
        return cast(str, response.text)
