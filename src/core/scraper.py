import base64
import binascii
import logging
import os
import random
import re
import time
from typing import Any
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from src.core.egress_manager import EgressManager, FetchExhausted
from src.core.schema_monitor import SchemaHealthMonitor

logger = logging.getLogger("Scraper")


class CircuitBreaker:
    """Prevents hammering Cloudflare when fully blocked."""

    failures: int
    threshold: int
    cooldown: int
    last_failure: float | None
    is_open: bool

    def __init__(
        self, failure_threshold: int | None = None, cooldown_seconds: int | None = None
    ) -> None:
        self.failures = 0
        # Precedence: Explicit Arg > Env Var > Default
        if failure_threshold is not None:
            self.threshold = failure_threshold
        else:
            self.threshold = int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", 3))

        if cooldown_seconds is not None:
            self.cooldown = cooldown_seconds
        else:
            self.cooldown = int(os.getenv("CIRCUIT_BREAKER_COOLDOWN", 300))

        self.last_failure: float | None = None
        self.is_open = False

    def record_success(self) -> None:
        """Reset circuit breaker on successful request."""
        self.failures = 0
        self.is_open = False

    def record_failure(self) -> None:
        """Track failures and open circuit if threshold exceeded."""
        self.failures += 1
        self.last_failure = time.time()
        if self.failures >= self.threshold:
            self.is_open = True
            logger.warning(f"⚠️ Circuit breaker OPEN. Pausing {self.cooldown}s...")

    def can_attempt(self) -> bool:
        """Check if we can attempt a request."""
        if not self.is_open:
            return True
        # Check if cooldown expired
        if self.last_failure and time.time() - self.last_failure > self.cooldown:
            logger.info("Circuit breaker RESET. Resuming...")
            self.is_open = False
            self.failures = 0
            return True
        return False



class BindScraper:
    # Allow override via env var (Issue #1 from Audit)
    BASE_URL = os.getenv("ABB_URL", "http://audiobookbay.lu")

    # Network Configuration
    REQUEST_TIMEOUT = 30  # seconds - prevents indefinite hangs
    MAX_RETRIES = 3  # attempts before giving up

    def __init__(self, egress_manager: EgressManager | None = None) -> None:
        self.circuit_breaker = CircuitBreaker()
        self.egress = egress_manager or EgressManager.from_env()
        self.schema_monitor = SchemaHealthMonitor()

    def _get_page(self, url: str) -> str | None:
        """
        Fetch a page via the egress manager (three-layer waterfall with retry).
        Circuit breaker gates the entire attempt; only opens after all egress
        paths and all retries are exhausted.
        """
        if not self.circuit_breaker.can_attempt():
            logger.error("⛔ Circuit breaker OPEN. Skipping request.")
            return None

        delay = random.uniform(2.0, 5.0)
        logger.debug(f"Sleeping for {delay:.2f}s...")
        time.sleep(delay)

        try:
            result = self.egress.fetch(url)
            self.circuit_breaker.record_success()
            return result
        except FetchExhausted:
            logger.error(f"All egress paths exhausted for {url}")
            self.circuit_breaker.record_failure()
            return None

    def search(self, term: str) -> list[dict[str, Any]]:
        """
        Searches ABB for a term.
        """
        search_url = f"{self.BASE_URL}/?s={quote_plus(term)}"
        html = self._get_page(search_url)
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        results = []

        for item in soup.select(".post"):
            title_elem = item.select_one(".postTitle h2 a")
            if title_elem:
                title = title_elem.text.strip()
                link = title_elem["href"]
                results.append({"title": title, "link": link, "hash": None})
        return results

    def extract_info_hash(self, detail_page_url: str) -> str | None:
        """
        Fetches a detail page and extracts the Info Hash using a ranked
        4-strategy waterfall. Each strategy outcome is recorded by the
        SchemaHealthMonitor for drift detection.
        """
        if not detail_page_url.startswith("http"):
            detail_page_url = f"{self.BASE_URL}{detail_page_url}"

        html = self._get_page(detail_page_url)
        if not html:
            return None

        soup = BeautifulSoup(html, "html.parser")

        strategies: list[tuple[str, Any]] = [
            ("td_exact", self._parse_hash_table_td),
            ("th_exact", self._parse_hash_table_th),
            ("magnet_href", self._parse_hash_magnet_href),
            ("regex_fullpage", self._parse_hash_text_search),
        ]

        for strategy_name, strategy_fn in strategies:
            result = strategy_fn(soup, detail_page_url)
            if result:
                self.schema_monitor.record(detail_page_url, strategy_name, True)
                return str(result)
            self.schema_monitor.record(detail_page_url, strategy_name, False)

        logger.warning(f"All parse strategies failed for {detail_page_url}")
        return None

    def _parse_hash_table_td(self, soup: BeautifulSoup, url: str) -> str | None:
        """Primary: <td>Info Hash:</td> followed by sibling <td>."""
        hash_row = soup.find("td", string="Info Hash:")
        if hash_row:
            sibling = hash_row.find_next_sibling("td")
            if sibling:
                return self._ensure_hex(sibling.text.strip())
            logger.debug(f"[td_exact] Label found but no value cell on {url}")
        return None

    def _parse_hash_table_th(self, soup: BeautifulSoup, url: str) -> str | None:
        """Fallback 1: <th>Info Hash:</th> followed by sibling <td>."""
        hash_row = soup.find("th", string="Info Hash:")
        if hash_row:
            sibling = hash_row.find_next_sibling("td")
            if sibling:
                return self._ensure_hex(sibling.text.strip())
            logger.debug(f"[th_exact] Label found but no value cell on {url}")
        return None

    def _parse_hash_magnet_href(self, soup: BeautifulSoup, url: str) -> str | None:
        """Fallback 2: extract info hash from an existing magnet: link on the page."""
        for tag in soup.find_all("a", href=True):
            href = tag["href"]
            if href.startswith("magnet:"):
                match = re.search(r"urn:btih:([0-9a-fA-F]{40}|[A-Z2-7]{32})", href)
                if match:
                    return self._ensure_hex(match.group(1))
        return None

    def _parse_hash_text_search(self, soup: BeautifulSoup, url: str) -> str | None:
        """Fallback 3: regex scan of full page text for a 40-char hex info hash."""
        text = soup.get_text()
        match = re.search(r"\b([0-9a-fA-F]{40})\b", text)
        if match:
            return match.group(1).lower()
        return None

    def get_recent_books(self) -> list[dict[str, str]]:
        rss_url = f"{self.BASE_URL}/rss"
        xml = self._get_page(rss_url)
        if not xml:
            return []

        soup = BeautifulSoup(xml, "xml")
        items = []
        for item in soup.find_all("item"):
            # Defensive: check title and link exist before accessing .text
            if item.title and item.link:
                title = item.title.text
                link = item.link.text
                items.append({"title": title, "link": link})
            else:
                # Log but don't crash - skip malformed items
                logger.warning("Skipping RSS item with missing title or link")

        return items

    def _ensure_hex(self, bg_hash: str | None) -> str | None:
        """
        Converts Base32 to Hex if necessary (Research Section 3.3).
        """
        if not bg_hash:
            return None

        clean_hash = bg_hash.strip()

        # Already Hex
        if len(clean_hash) == 40:
            return clean_hash.lower()

        # Base32
        elif len(clean_hash) == 32:
            try:
                logger.info(f"Detected Base32 hash: {clean_hash}, converting to Hex.")
                return base64.b16encode(base64.b32decode(clean_hash)).decode("utf-8").lower()
            except binascii.Error:
                logger.warning(f"Invalid Base32 hash encountered: {clean_hash}")
                return None

        return None

    @classmethod
    def generate_magnet(cls, info_hash: str, title: str, trackers: list[str]) -> str:
        """
        Generates a robust magnet link with trackers.
        Title is URL-encoded to handle special characters (&, +, =, ?, #, spaces, etc.)
        """
        # URL-encode title to prevent broken links when title contains special characters
        # quote_plus() encodes spaces as '+' and special chars as '%XX'
        title_encoded = quote_plus(title)

        magnet = f"magnet:?xt=urn:btih:{info_hash}&dn={title_encoded}"
        for tr in trackers:
            magnet += f"&tr={tr}"
        return magnet
