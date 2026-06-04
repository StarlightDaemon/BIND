```gemini-3.1-pro
You are adding pytest tests to the BIND project to improve code coverage.
Working directory: /mnt/e/BIND
Activate the venv before running anything: source .venv/bin/activate

## Your task

Append new test classes to `tests/test_scraper.py` covering the network layer
and RSS parsing in `src/core/scraper.py`. Do NOT modify existing tests.

## Coverage targets — missing lines

```
src/core/scraper.py   Missing: 87-102, 111, 115, 175-192, 194-211
```

Map to code:
- 87–89   → `_get_page()` — circuit breaker is open → returns None immediately
- 91–93   → `_get_page()` — `time.sleep` + delay before fetch
- 95–98   → `_get_page()` — `egress.fetch()` returns HTML → `record_success()` → returns result
- 99–102  → `_get_page()` — `egress.fetch()` raises `FetchExhausted` → `record_failure()` → returns None
- 111     → `extract_info_hash()` — relative URL gets `base_url` prefix prepended
- 115     → `extract_info_hash()` — `_get_page()` returns None → returns None immediately
- 175–192 → `get_recent_books()` — full path: fetch RSS XML, parse items, handle missing title/link
- 194–211 → `probe_target()` — all four return branches: cloudflare_block, wrong_content, reachable, unreachable

## Key files to read before writing

- `src/core/scraper.py` full file
- `src/core/egress_manager.py` (to understand `EgressManager` and `FetchExhausted`)
- `tests/test_scraper.py` (existing tests to understand patterns)
- `tests/conftest.py`

## Critical facts

1. **Instantiate BindScraper with a mock EgressManager** to avoid real network calls:
   ```python
   from unittest.mock import MagicMock
   from src.core.egress_manager import FetchExhausted
   from src.core.scraper import BindScraper

   def _make_scraper(fetch_result=None, fetch_raises=None):
       egress = MagicMock()
       if fetch_raises:
           egress.fetch.side_effect = fetch_raises
       else:
           egress.fetch.return_value = fetch_result
       egress._cffi_session = MagicMock()
       return BindScraper(egress_manager=egress)
   ```

2. **`_get_page` circuit breaker open (line 87–89):** Set `scraper.circuit_breaker.is_open = True` and `scraper.circuit_breaker.last_failure = time.time()` BEFORE calling `_get_page`. Result must be `None` and `egress.fetch` must NOT be called.

3. **`_get_page` fetch delay (line 91–93):** Patch `time.sleep` to avoid the 2–5s delay:
   ```python
   with patch("src.core.scraper.time.sleep"):
       result = scraper._get_page("http://example.com/page")
   ```

4. **`_get_page` success path (lines 95–98):** `egress.fetch` returns `"<html>ok</html>"`. Verify `scraper.circuit_breaker.failures == 0` and return value equals the HTML string.

5. **`_get_page` FetchExhausted (lines 99–102):** `egress.fetch.side_effect = FetchExhausted()`. Verify return is `None` and `scraper.circuit_breaker.is_open` becomes `True` after threshold failures.

6. **`extract_info_hash` relative URL (line 111):** Pass `"/audio-books/test/"` (no `http`). Patch `_get_page` to return valid HTML. The scraper must prepend `scraper.base_url` before fetching.

7. **`extract_info_hash` html=None (line 115):** Patch `_get_page` to return `None`. Result must be `None`.

8. **`get_recent_books` (lines 175–192):** Patch `_get_page` to return a valid RSS 2.0 XML string. Verify the returned list contains dicts with `"title"` and `"link"` keys. Also provide an RSS XML with one `<item>` missing `<link>` to hit the warning branch. RSS XML fixture:
   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <rss version="2.0">
     <channel>
       <title>AudioBookBay</title>
       <item>
         <title>Test Book One</title>
         <link>http://audiobookbay.lu/audio-books/test-one/</link>
       </item>
       <item>
         <title>No Link Book</title>
       </item>
     </channel>
   </rss>
   ```
   Expect 1 item returned (the one with a link), and the malformed item logged as a warning.

9. **`get_recent_books` returns empty on None (line 177):** Patch `_get_page` to return `None`. Expect `[]`.

10. **`probe_target` (lines 194–211):** Mock `egress._cffi_session.get(...)` return value:
    - `response.text` contains `"Just a moment..."` → `"cloudflare_block"`
    - `response.text` is `"<html>something unrelated</html>"` → `"wrong_content"`
    - `response.text` is `"<html>audiobookbay content here</html>"` → `"reachable"`
    - `.get()` raises `Exception("timeout")` → `"unreachable"`

## Classes to write

```python
class TestGetPage:
    # test_returns_none_when_circuit_breaker_open
    # test_returns_html_on_successful_fetch
    # test_returns_none_and_records_failure_on_fetch_exhausted
    # test_calls_sleep_before_fetching

class TestExtractInfoHashNetwork:
    # test_prepends_base_url_for_relative_links
    # test_returns_none_when_page_fetch_fails

class TestGetRecentBooks:
    # test_returns_empty_list_when_fetch_fails
    # test_parses_rss_items_correctly
    # test_skips_items_missing_link
    # test_returns_list_of_title_and_link_dicts

class TestProbeTarget:
    # test_returns_cloudflare_block
    # test_returns_wrong_content
    # test_returns_reachable
    # test_returns_unreachable_on_exception
```

## Validation

After writing, run:
```
python -m pytest tests/test_scraper.py -v --cov=src/core/scraper --cov-report=term-missing
```
Target: `src/core/scraper.py` coverage above 80%.  
All tests must pass. Report the final coverage line.
```
