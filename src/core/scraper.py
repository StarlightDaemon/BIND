import cloudscraper
from bs4 import BeautifulSoup
import logging
import base64
import binascii
import time
import random
import os
from urllib.parse import quote_plus

logger = logging.getLogger("Scraper")

class CircuitBreaker:
    """Prevents hammering Cloudflare when fully blocked."""
    def __init__(self, failure_threshold=3, cooldown_seconds=300):
        self.failures = 0
        self.threshold = int(os.getenv('CIRCUIT_BREAKER_THRESHOLD', failure_threshold))
        self.cooldown = int(os.getenv('CIRCUIT_BREAKER_COOLDOWN', cooldown_seconds))
        self.last_failure = None
        self.is_open = False
    
    def record_success(self):
        """Reset circuit breaker on successful request."""
        self.failures = 0
        self.is_open = False
    
    def record_failure(self):
        """Track failures and open circuit if threshold exceeded."""
        self.failures += 1
        self.last_failure = time.time()
        if self.failures >= self.threshold:
            self.is_open = True
            logger.warning(f"⚠️ Circuit breaker OPEN. Pausing {self.cooldown}s...")
    
    def can_attempt(self):
        """Check if we can attempt a request."""
        if not self.is_open:
            return True
        # Check if cooldown expired
        if time.time() - self.last_failure > self.cooldown:
            logger.info("Circuit breaker RESET. Resuming...")
            self.is_open = False
            self.failures = 0
            return True
        return False

class ScraperMetrics:
    """Track success/failure rates per scraping layer."""
    def __init__(self):
        self.attempts = {'curl_cffi': 0, 'curl_cffi_proxy': 0, 'cloudscraper': 0}
        self.successes = {'curl_cffi': 0, 'curl_cffi_proxy': 0, 'cloudscraper': 0}
        self.failures = {'curl_cffi': 0, 'curl_cffi_proxy': 0, 'cloudscraper': 0}
    
    def record(self, layer, success):
        """Record attempt outcome."""
        self.attempts[layer] += 1
        if success:
            self.successes[layer] += 1
        else:
            self.failures[layer] += 1
    
    def report(self):
        """Log summary statistics."""
        for layer in self.attempts:
            total = self.attempts[layer]
            if total > 0:
                rate = (self.successes[layer] / total) * 100
                logger.info(f"📊 {layer}: {rate:.1f}% success ({self.successes[layer]}/{total})")

class BindScraper:
    # Allow override via env var (Issue #1 from Audit)
    BASE_URL = os.getenv('ABB_URL', "http://audiobookbay.lu")
    
    # Network Configuration
    REQUEST_TIMEOUT = 30  # seconds - prevents indefinite hangs
    MAX_RETRIES = 3       # attempts before giving up
    
    # Trackers from Research (Section 3.4)
    TRACKERS = [
        "udp://tracker.opentrackr.org:1337/announce",
        "udp://tracker.openbittorrent.com:80/announce",
        "udp://9.rarbg.to:2710/announce",
        "http://tracker.openbittorrent.com:80/announce",
        "udp://tracker.coppersurfer.tk:6969/announce"
    ]
    
    def __init__(self):
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )
        # Phase 2: Proxy and Resilience
        self.proxy = os.getenv('BIND_PROXY')  # Optional: HTTP/SOCKS5 proxy
        self.circuit_breaker = CircuitBreaker()
        self.metrics = ScraperMetrics()
        
        if self.proxy:
            logger.info(f"🔒 Proxy configured: {self.proxy.split('@')[-1] if '@' in self.proxy else self.proxy}")
    
    def _get_page(self, url):
        """
        Fetch a page using Phase 2 Waterfall strategy with circuit breaker.
        
        Layers:
        1. curl_cffi (primary - fast TLS masquerading)
        2. curl_cffi + proxy (IP ban bypass)
        3. cloudscraper (legacy fallback)
        
        Returns HTML text on success, None on failure.
        """
        # Circuit breaker check
        if not self.circuit_breaker.can_attempt():
            logger.error("⛔ Circuit breaker OPEN. Skipping request.")
            return None
        
        # Politeness delay
        delay = random.uniform(2.0, 5.0)
        logger.debug(f"Sleeping for {delay:.2f}s...")
        time.sleep(delay)
        
        # LAYER 1: curl_cffi (Primary)
        try:
            response = self._attempt_curl_cffi(url, use_proxy=False)
            self.metrics.record('curl_cffi', True)
            self.circuit_breaker.record_success()
            logger.debug(f"✓ Fetched {url} (curl_cffi)")
            return response
        except Exception as e:
            self.metrics.record('curl_cffi', False)
            logger.warning(f"curl_cffi failed: {type(e).__name__}")
        
        # LAYER 2: curl_cffi + Proxy (if configured)
        if self.proxy:
            try:
                response = self._attempt_curl_cffi(url, use_proxy=True)
                self.metrics.record('curl_cffi_proxy', True)
                self.circuit_breaker.record_success()
                logger.info(f"✓ Fetched {url} (curl_cffi + proxy)")
                return response
            except Exception as e:
                self.metrics.record('curl_cffi_proxy', False)
                logger.warning(f"curl_cffi+proxy failed: {type(e).__name__}")
        
        # LAYER 3: cloudscraper (Legacy fallback)
        try:
            response = self._attempt_cloudscraper(url)
            self.metrics.record('cloudscraper', True)
            self.circuit_breaker.record_success()
            logger.info(f"✓ Fetched {url} (cloudscraper)")
            return response
        except Exception as e:
            self.metrics.record('cloudscraper', False)
            logger.error(f"All layers failed for {url}: {type(e).__name__}")
        
        # Complete failure
        self.circuit_breaker.record_failure()
        return None
    
    def _attempt_curl_cffi(self, url, use_proxy=False):
        """Attempt to fetch using curl_cffi."""
        from curl_cffi import requests as cffi_requests
        
        proxy = self.proxy if use_proxy else None
        response = cffi_requests.get(
            url,
            impersonate="chrome120",
            proxy=proxy,
            timeout=self.REQUEST_TIMEOUT
        )
        response.raise_for_status()
        
        # Detect soft blocks
        if "Just a moment..." in response.text or "Attention Required" in response.text:
            raise ValueError("Cloudflare block detected")
        
        return response.text
    
    def _attempt_cloudscraper(self, url):
        """Attempt to fetch using cloudscraper."""
        response = self.scraper.get(url, timeout=self.REQUEST_TIMEOUT)
        response.raise_for_status()
        
        # Detect soft blocks
        if "Just a moment..." in response.text or "Attention Required" in response.text:
            raise ValueError("Cloudflare block detected")
        
        return response.text

    def search(self, term):
        """
        Searches ABB for a term.
        """
        search_url = f"{self.BASE_URL}/?s={term}"
        html = self._get_page(search_url)
        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        for item in soup.select('.post'):
            title_elem = item.select_one('.postTitle h2 a')
            if title_elem:
                title = title_elem.text.strip()
                link = title_elem['href']
                results.append({
                    'title': title,
                    'link': link,
                    'hash': None 
                })
        return results

    def extract_info_hash(self, detail_page_url):
        """
        Fetches a detail page and extracts the Info Hash.
        Defensive parsing: handles missing or changed HTML structure.
        """
        if not detail_page_url.startswith('http'):
            detail_page_url = f"{self.BASE_URL}{detail_page_url}"
            
        html = self._get_page(detail_page_url)
        if not html:
            return None
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # Look for "Info Hash:" label in table
        hash_row = soup.find('td', string='Info Hash:')
        if hash_row:
            # Defensive: check sibling exists before accessing .text
            sibling = hash_row.find_next_sibling('td')
            if sibling:
                raw_hash = sibling.text.strip()
                return self._ensure_hex(raw_hash)
            else:
                logger.warning(f"Found 'Info Hash:' label but no value cell on {detail_page_url}")
        else:
            logger.warning(f"Could not find 'Info Hash:' on {detail_page_url}")
        
        return None

    def get_recent_books(self):
        rss_url = f"{self.BASE_URL}/rss"
        xml = self._get_page(rss_url)
        if not xml:
            return []
            
        soup = BeautifulSoup(xml, 'xml')
        items = []
        for item in soup.find_all('item'):
            # Defensive: check title and link exist before accessing .text
            if item.title and item.link:
                title = item.title.text
                link = item.link.text
                items.append({'title': title, 'link': link})
            else:
                # Log but don't crash - skip malformed items
                logger.warning(f"Skipping RSS item with missing title or link")
            
        return items

    def _ensure_hex(self, bg_hash):
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
                return base64.b16encode(base64.b32decode(clean_hash)).decode('utf-8').lower()
            except binascii.Error:
                logger.warning(f"Invalid Base32 hash encountered: {clean_hash}")
                return None
                
        return None

    @classmethod
    def generate_magnet(cls, info_hash, title):
        """
        Generates a robust magnet link with trackers.
        Title is URL-encoded to handle special characters (&, +, =, ?, #, spaces, etc.)
        """
        # URL-encode title to prevent broken links when title contains special characters
        # quote_plus() encodes spaces as '+' and special chars as '%XX'
        title_encoded = quote_plus(title)
        
        magnet = f"magnet:?xt=urn:btih:{info_hash}&dn={title_encoded}"
        for tr in cls.TRACKERS:
            magnet += f"&tr={tr}"
        return magnet
