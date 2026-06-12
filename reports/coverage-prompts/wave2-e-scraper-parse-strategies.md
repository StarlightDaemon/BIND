# Group E — scraper.py: Parse Strategies + _ensure_hex Edge Cases

**Model: 🔵 Claude Sonnet** (reassigned from Gemini 3 Flash — Gemini models no longer available)
**Prereq: Wave 1 Group D committed** ✅ (both append to `tests/test_scraper.py`)
**Working directory:** `/Users/dante/Citadel/BIND`
**Activate the venv before running anything:** `source .venv/bin/activate`

You are adding pytest tests to the BIND project to improve code coverage.

## Your task

Append new test classes to `tests/test_scraper.py` covering the four parse
strategy methods and `_ensure_hex` edge cases in `src/core/scraper.py`.
Do NOT modify any existing tests.

## Coverage targets — missing lines

```
src/core/scraper.py   Missing: 140-143, 149-153, 159-163, 169-171, 218, 228-233
```

(Line numbers from the audit-time coverage run — if they have drifted, locate by
method name and confirm against a fresh `--cov-report=term-missing` run first.)

Map to methods:
- 140–143 → `_parse_hash_table_td()` — `<td>Info Hash:</td>` sibling found → returns hex
- 149–153 → `_parse_hash_table_th()` — `<th>Info Hash:</th>` sibling found → returns hex
- 159–163 → `_parse_hash_magnet_href()` — `<a href="magnet:?xt=urn:btih:...">` found → returns hex
- 169–171 → `_parse_hash_text_search()` — 40-char hex found in page text → returns it
- 218     → `_ensure_hex()` — input is `None` or empty string → returns `None`
- 228–233 → `_ensure_hex()` — 32-char Base32 string → converts to hex (success + invalid)

## Key facts

1. These are all **pure methods** that take a `BeautifulSoup` object and a URL string.
   Call them directly — no network mocks needed.
2. Import BeautifulSoup: `from bs4 import BeautifulSoup`
3. All methods have signature: `(self, soup: BeautifulSoup, url: str) -> str | None`
4. `_ensure_hex` has signature: `(self, bg_hash: str | None) -> str | None`
5. Create a `BindScraper()` instance with no args (circuit breaker + egress manager are
   not called by these methods).
6. A valid 40-char hex hash for fixtures: `"abc123def456789012345678901234567890abcd"`
7. A valid 32-char Base32 string (maps to known hex): `"MFRA"` is too short — use a
   proper 32-char Base32. Generate one:
   ```python
   import base64, binascii
   raw = bytes.fromhex("abc123def456789012345678901234567890abcd")
   b32 = base64.b32encode(raw).decode()  # gives a 32-char string
   ```
   Then verify `_ensure_hex(b32)` returns `"abc123def456789012345678901234567890abcd"`.

## HTML fixtures to use

```python
# For _parse_hash_table_td
TD_HTML = """<html><body><table><tr>
    <td>Info Hash:</td><td>abc123def456789012345678901234567890abcd</td>
</tr></table></body></html>"""

# For _parse_hash_table_th
TH_HTML = """<html><body><table><tr>
    <th>Info Hash:</th><td>abc123def456789012345678901234567890abcd</td>
</tr></table></body></html>"""

# For _parse_hash_magnet_href
MAGNET_HTML = """<html><body>
    <a href="magnet:?xt=urn:btih:abc123def456789012345678901234567890abcd&dn=Test">Download</a>
</body></html>"""

# For _parse_hash_text_search
TEXT_HTML = """<html><body>
    <p>The info hash is abc123def456789012345678901234567890abcd for this release.</p>
</body></html>"""

# For negative cases (no match)
EMPTY_HTML = "<html><body><p>Nothing here.</p></body></html>"
```

## Classes to write

```python
class TestParseHashTableTd:
    # test_returns_hash_when_td_label_and_sibling_present
    # test_returns_none_when_no_info_hash_td

class TestParseHashTableTh:
    # test_returns_hash_when_th_label_and_sibling_present
    # test_returns_none_when_no_info_hash_th

class TestParseHashMagnetHref:
    # test_returns_hash_from_magnet_link
    # test_returns_none_when_no_magnet_link

class TestParseHashTextSearch:
    # test_returns_hash_from_page_text
    # test_returns_none_when_no_hex_in_text

class TestEnsureHexEdgeCases:
    # test_returns_none_for_none_input
    # test_returns_none_for_empty_string
    # test_converts_valid_base32_to_hex
    # test_returns_none_for_invalid_base32
    # test_returns_none_for_wrong_length  (e.g., 10-char string)
```

## Validation

After writing, run:
```
python -m pytest tests/test_scraper.py -v --cov=src/core/scraper --cov-report=term-missing
```
All tests must pass. Confirm lines 140-143, 149-153, 159-163, 169-171, 218, 228-233
are no longer in the Missing column. Report the final coverage percentage.
