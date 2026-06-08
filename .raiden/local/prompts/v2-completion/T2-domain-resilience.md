# T2 — Domain Change Resilience Probe

## Prompt ID

`bind.v2.T2.domain-resilience.v1`

## Purpose

Add a lightweight probe to `BindScraper` that distinguishes Cloudflare blocks
from domain changes, surfaces the result in `/health`, and logs a warning at
daemon startup when the target is unreachable or serving wrong content.

## Agent Type

**Claude Code** — multi-file Python implementation with tests.

## Model

**Primary:** `claude-sonnet-4-6`
Rationale: Multi-file change touching the scraper, daemon entrypoint, and
Flask server. Requires understanding the existing three-layer egress waterfall
and circuit breaker to add the probe without interfering with them. Sonnet
handles this scope well without over-engineering.

**Secondary:** `claude-opus-4-8`
Use if the probe logic requires deeper reasoning about edge cases in the
egress/circuit-breaker interaction, or if Sonnet's test coverage for the
probe is thin.

## Phase

Phase 1 — runs **in parallel** with T1 and T3. No dependencies on other tasks.
T3 touches `/health` only to add a `target_probe` field; verify no conflict.

---

## Prompt

You are working in the repository at `/Users/dante/Citadel/BIND`.

BIND is a Python audiobook metadata daemon (v1.7.1) that scrapes AudioBookBay
(ABB) and serves an RSS feed via Flask/Gunicorn.

### Background

AudioBookBay migrates domains periodically (current default: `audiobookbay.lu`
via `ABB_URL` env var). The scraper has a circuit breaker that trips after
repeated failures, but it cannot distinguish:

- **Cloudflare soft-block** — temporary; response body contains
  `"Just a moment..."`, `"Attention Required"`, or `"cf-browser-verification"`
- **Domain unreachable** — DNS failure, connection timeout, HTTP 5xx
- **Wrong content** — HTTP 200 but not an ABB page (domain expired/hijacked)

All three currently look identical at the circuit breaker level.

### Key Files

- `src/core/scraper.py` — `BindScraper` class; `self.base_url` from `ABB_URL`
- `src/core/egress_manager.py` — `EgressManager`; `self._cffi_session`
- `src/bind.py` — daemon entrypoint; `schedule` loop; `run_job_with_timeout()`
- `src/rss_server.py` — Flask app; `/health` route

### Task

#### 1. `BindScraper.probe_target()` in `src/core/scraper.py`

Add an instance method `probe_target() -> str` that returns exactly one of:
`"reachable"`, `"cloudflare_block"`, `"unreachable"`, `"wrong_content"`.

Rules:
- Makes a **single GET request** to `self.base_url` using
  `self.egress._cffi_session.get(url, timeout=10)` directly — do NOT go
  through the egress waterfall or circuit breaker. This is a probe, not a
  scrape; it must not trip or consume circuit breaker state.
- `"cloudflare_block"`: response received, body contains any of:
  `"Just a moment..."`, `"Attention Required"`, `"cf-browser-verification"`
- `"wrong_content"`: response received, no Cloudflare strings, but none of
  `"audiobookbay"`, `"AudioBookBay"` appear in the first 4096 bytes of the
  body (case-insensitive check on `body[:4096].lower()`)
- `"unreachable"`: any exception (connection error, timeout, DNS failure)
- `"reachable"`: HTTP 200 and ABB content markers found

Catch broadly (`except Exception`) and return `"unreachable"` on any error.
Do not raise.

#### 2. Daemon startup warning in `src/bind.py`

In the `daemon()` command function, before the `schedule.every(...).do(...)`
call, add:

```python
probe_result = scraper.probe_target()
if probe_result in ("unreachable", "wrong_content"):
    logger.warning(
        "Target domain probe returned '%s'. "
        "Check ABB_URL config. Current: %s",
        probe_result,
        scraper.base_url,
    )
```

Do not abort startup. The circuit breaker handles degradation; this is
advisory only.

#### 3. Cached probe in `/health` in `src/rss_server.py`

Add a module-level cache:

```python
_probe_cache: dict[str, Any] = {"result": None, "expires": 0.0}
```

In the `/health` route, before building the response dict, check the cache:
- If `time.monotonic() > _probe_cache["expires"]`, run
  `BindScraper().probe_target()`, store the result, set
  `expires = time.monotonic() + 300` (5 minutes)
- Add `"target_probe": _probe_cache["result"]` to the response dict

Import `time` at the top of the file if not already imported.
Instantiating `BindScraper()` for the probe is acceptable; it shares no
state with the daemon process.

#### 4. Tests in `tests/test_scraper_probe.py`

Write at minimum four test cases using `pytest-mock`:

- Mock `self.egress._cffi_session.get` to return a response with body
  `"Just a moment..."` → assert return value is `"cloudflare_block"`
- Mock to return body `"<html>some other site</html>"` (no ABB markers) →
  assert `"wrong_content"`
- Mock to raise `ConnectionError` → assert `"unreachable"`
- Mock to return body containing `"audiobookbay"` → assert `"reachable"`

Use `unittest.mock.MagicMock` or `mocker.patch` consistently with existing
test style (check `tests/` for convention).

### Exit Criteria

- `probe_target()` exists on `BindScraper`; returns one of the four strings
- Daemon startup logs a WARNING for `"unreachable"` or `"wrong_content"`
- `/health` JSON includes `"target_probe"` (cached, max one network call per
  5 minutes per process)
- `tests/test_scraper_probe.py` has ≥4 tests, all passing
- `pytest` full suite passes with no regressions
- `mypy src/` passes
- `ruff check src/ tests/` passes
