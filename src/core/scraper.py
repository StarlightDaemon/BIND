import cloudscraper
from bs4 import BeautifulSoup
import logging
import base64
import binascii
import time
import random

logger = logging.getLogger("Scraper")

class BindScraper:
    BASE_URL = "http://audiobookbay.lu"
    
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
    
    def _get_page(self, url):
        try:
            # Politeness Delay (Research Section 5.3)
            # Random delay between requests to avoid WAF analysis
            delay = random.uniform(2.0, 5.0) 
            logger.debug(f"Sleeping for {delay:.2f}s...")
            time.sleep(delay)
            
            logger.debug(f"Fetching: {url}")
            response = self.scraper.get(url)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None

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
        """
        if not detail_page_url.startswith('http'):
            detail_page_url = f"{self.BASE_URL}{detail_page_url}"
            
        html = self._get_page(detail_page_url)
        if not html:
            return None
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # Look for "Info Hash:" or similar markers
        # The structure might vary, so we look for the label
        hash_row = soup.find('td', string='Info Hash:')
        if hash_row:
            raw_hash = hash_row.find_next_sibling('td').text.strip()
            return self._ensure_hex(raw_hash)
        
        return None

    def get_recent_books(self):
        rss_url = f"{self.BASE_URL}/rss"
        xml = self._get_page(rss_url)
        if not xml:
            return []
            
        soup = BeautifulSoup(xml, 'xml')
        items = []
        for item in soup.find_all('item'):
            title = item.title.text
            link = item.link.text
            items.append({'title': title, 'link': link})
            
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
        """
        magnet = f"magnet:?xt=urn:btih:{info_hash}&dn={title}"
        for tr in cls.TRACKERS:
            magnet += f"&tr={tr}"
        return magnet
