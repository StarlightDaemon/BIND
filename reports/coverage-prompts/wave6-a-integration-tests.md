# Wave 6-A — Integration Tests: Sentinels, Config Round-Trip, Control Plane

**Model: Claude Opus**
**Dependencies:** Waves 5-A and 5-B **committed** (these tests target the post-rework control plane: `loop_tick`, `LiveConfig`, heartbeat).
**Working directory:** `/Users/dante/Citadel/BIND`
**Activate the venv before any shell commands:** `source .venv/bin/activate`
**Finding remediated:** TEST-3 (integration-test half; the loop-extraction half shipped in Wave 5-B) from `BIND_FULL_AUDIT_REPORT.md`.

## Why Opus for this task

These tests exercise the daemon ↔ RSS-server seam through the real filesystem and real SQLite — the layer where every Wave-5 bug lived. Vacuously-passing integration tests (mocking away the very interaction under test) are worse than no tests; the design judgment is what to keep real.

## Background

`tests/integration/` is empty (literally — only `__pycache__`). The unit suite reached 97.5% line coverage while the three cross-process behaviors the audit flagged had zero coverage. Wave 5-B extracted the daemon loop body (`loop_tick` or equivalent — read the current `src/bind.py` first and adapt names to what actually landed).

## Task — create `tests/integration/` suite

Ground rules: real `tmp_path` filesystem, real SQLite `MagnetStore`, real `ConfigManager`/`LiveConfig` pointed at tmp paths, real Flask test client. Mock ONLY network egress (`BindScraper`/`EgressManager`) and `subprocess.run` (systemctl). No `time.sleep` longer than ~0.1s — drive ticks synchronously by calling the extracted loop function.

### 1. `test_sentinel_ipc.py` — trigger lifecycle across the seam

- RSS side touches `.trigger` via `POST /api/trigger-scrape` (real route, real tmp data dir) → daemon `loop_tick` consumes it → asserts the job ran (mocked scraper invoked) and the file is gone.
- Trigger while daemon "down": touch via route, run NO ticks, second POST → 409 (fresh) ; age the file's mtime past 2× interval (`os.utime`) → POST returns 200-with-replacement (Wave 5-B behavior).
- Startup cleanup: pre-place `.trigger` + `.enable-scraping`, run daemon startup path → both deleted, exactly one startup job (not two — this is the ARCH-3 double-scrape regression test).

### 2. `test_config_roundtrip.py` — write → live-read seam

- RSS `POST /api/settings` (real route, real config file in tmp) → assert the file on disk parses back with every submitted value AND preserves an admin-managed key + a non-UI `DEFAULTS` key (`BIND_DB_PATH=/custom/x.db`) planted beforehand (ARCH-4 regression at integration level).
- `SCRAPING_ENABLED` live transition: config true → tick (job scheduled) → RSS writes false via the real settings route → next tick → assert schedule cleared, daemon state `disabled`, heartbeat row says `disabled`. Then `POST /api/scraping/enable` → tick → scraping resumes. **This is the end-to-end ARCH-2 proof.**
- `restart_daemon` mocked `subprocess.run` raising `FileNotFoundError` → settings POST still 200 with the honest message (Docker path).

### 3. `test_auth_flags_live.py` — SEC-2 regression at the seam

- With auth enabled at process-start-env level unset: flip `BIND_AUTH_ENABLED` true↔false **in the config file** between two requests to a protected route → assert 401 appears/disappears without any restart or re-import. Use `LiveConfig`'s injection point; do not reach into private cache state.
- Precedence: set the key in env-snapshot (via the documented injection/monkeypatch seam from Wave 5-B) → config-file flips no longer matter. Locks the precedence contract.

### 4. `test_heartbeat_seam.py` — ARCH-1 across processes

- Daemon ticks write beats into the tmp DB → a *separately constructed* `MagnetStore` (simulating the RSS process) reads them → `check_daemon_status` returns online; advance the clock source (monkeypatch the time the reader compares against, not sleep) → offline.
- No-row fallback: fresh DB, no beat → mtime fallback engages (plant a log file) → status matches legacy behavior.

### Infrastructure

- A `tests/integration/conftest.py` with a `control_plane` fixture assembling the tmp data dir, config file, store, LiveConfig, daemon context, and Flask client wired to the same paths. Keep it under ~80 lines; if it grows past that, the production seams are too narrow — fix the seam (constructor injection), don't grow the fixture.
- Mark the module `@pytest.mark.integration`; register the mark in `pyproject.toml`. CI runs them by default (they're fast); the mark exists for selective local runs.

## Constraints

- Do not modify production code except to add missing constructor-injection seams, and list every such edit in your summary (each must be injection-only — no behavior change).
- Do not modify existing unit tests.
- Compose-based smoke tests (real containers) are explicitly OUT of scope — note them as future CI work in a comment.

## Verification

```bash
source .venv/bin/activate
python -m pytest tests/integration/ -q          # the new suite
python -m pytest tests/ -q                      # everything, still green
ruff check src/ tests/ && mypy src/
```

## Done criteria

All four modules pass; total runtime of `tests/integration/` under 10 seconds; the ARCH-2 end-to-end proof and ARCH-3 double-scrape regression are present and fail when run against pre-Wave-5 code (sanity-check the assertions reference the new behavior, since stashing across waves isn't practical here — state how you convinced yourself each test isn't vacuous).
