# Wave 4-D — Retry Engine: Real Exception Classification

**Model: Claude Opus**
**No dependencies** — runs independently. Sole owner of `src/core/retry.py`.
**Working directory:** `/Users/dante/Citadel/BIND`
**Activate the venv before any shell commands:** `source .venv/bin/activate`
**Finding remediated:** RES-2 from `BIND_FULL_AUDIT_REPORT.md` (repo root — read it in full first).

## Why Opus for this task

The original bug survived review and a green test suite precisely because exception-hierarchy reasoning across two HTTP libraries is subtle. The fix is small; proving it correct against the *actual* exception types each library raises is the work.

## The bug

`RetryEngine.execute` (`src/core/retry.py:71`) classifies transient network errors with:

```python
elif isinstance(e, (ConnectionError, TimeoutError)):
```

Those are Python **builtins**. Neither egress library raises them:
- `curl_cffi` raises its own hierarchy (`curl_cffi.requests.exceptions.RequestException` subtypes / `CurlError` carrying a libcurl error code).
- `cloudscraper`/`requests` raise `requests.exceptions.ConnectionError`/`Timeout`, which subclass `RequestException(IOError)` — **not** the builtin `ConnectionError`.

So every real connection failure or timeout falls into the final `else` ("Non-retryable … escalating") and gets **zero in-layer retries**. The documented "3 attempts with backoff per layer" exists only for HTTP-status errors. The existing unit tests raise builtins, masking the bug.

## Required behavior

1. **Investigate before coding.** In the venv, import both libraries and enumerate the concrete exception types for: connection refused, DNS failure, and timeout. For curl_cffi 0.15.0, check what `Session.get` raises on connect failure vs. timeout (inspect `curl_cffi.requests.exceptions` and `curl_cffi.CurlError`; note `CurlError.code` values — e.g. libcurl 6/7/28 — if relevant). For requests: `requests.exceptions.ConnectionError`, `requests.exceptions.Timeout` (and note `cloudscraper` may wrap or re-raise these — check its source in the venv). Record what you found in your summary.
2. **Classify transient errors by the real types.** Build an explicit tuple, e.g.:
   - `requests.exceptions.ConnectionError`, `requests.exceptions.Timeout`
   - the curl_cffi equivalents found in step 1 (timeout + connect classes, or `CurlError` filtered by transient `code`s if the hierarchy doesn't distinguish)
   - keep the builtins `ConnectionError, TimeoutError` in the tuple (harmless, preserves existing tests and any direct-socket future use).
   Keep the duck-typed `.response`/`status_code` HTTP classification above it exactly as-is — it already works and the ordering (HTTP status checks first) must not change.
3. **Import strategy.** `retry.py` currently imports neither library; importing both at module top couples the retry engine to the HTTP stack. Acceptable options: (a) lazy build of the transient-types tuple at first use with try/except ImportError per library, or (b) plain top-level imports with a comment (both libs are hard deps in requirements.txt). Choose (b) unless you find a reason not to — simplicity wins; document the choice.
4. **Regression tests** (append to `tests/test_retry.py` and/or `tests/test_resilience_extended.py`; do not modify existing tests):
   - A callable raising `requests.exceptions.ConnectionError` → retried `max_attempts` times (assert call count == 3, returns None after exhaustion, with `time.sleep` mocked).
   - Same for `requests.exceptions.Timeout`.
   - Same for the curl_cffi transient type(s) identified in step 1 — raise the **real** class, not a stand-in.
   - A `requests.exceptions.HTTPError` with a mocked `.response.status_code = 404` still escalates immediately (guards the ordering: these exception classes also pass `isinstance` checks loosely — the `.response` branch must win).
   - A genuinely foreign exception (`ValueError`) still escalates immediately (Cloudflare-marker path, `src/core/egress_manager.py:117`).

## Constraints

- Files in scope: `src/core/retry.py`, `tests/test_retry.py`, `tests/test_resilience_extended.py`.
- No behavior change for HTTP-status classification, 429/Retry-After handling, jitter, or the return-None contract (`EgressManager.fetch` at `src/core/egress_manager.py:102-110` depends on it).
- Mock `time.sleep` in all new tests — no real backoff delays in the suite.

## Verification

```bash
source .venv/bin/activate
python -m pytest tests/test_retry.py tests/test_resilience_extended.py tests/test_egress_manager.py -q
python -m pytest tests/ -q
ruff check src/ tests/ && mypy src/
```

## Done criteria

The new transient-type tests fail against the pre-change code (verify once by stashing); full suite green; your summary lists the exact exception classes per library and which libcurl codes (if any) you classified as transient.
