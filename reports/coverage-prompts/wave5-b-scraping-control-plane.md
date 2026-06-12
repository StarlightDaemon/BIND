# Wave 5-B — Scraping Control Plane: Single Source of Truth + Live Config

**Model: Claude Fable**
**Dependencies:** Wave 4-E **committed** (atomic `write_config` — this change reads config every loop tick and must never observe a half-written file). Do not run concurrently with Wave 5-A or 5-C (all touch `src/bind.py`).
**Working directory:** `/Users/dante/Citadel/BIND`
**Activate the venv before any shell commands:** `source .venv/bin/activate`
**Findings remediated:** ARCH-2, ARCH-3, SEC-2 (+ the loop-extraction half of TEST-3) from `BIND_FULL_AUDIT_REPORT.md` (repo root — read all three in full; ARCH-2 contains the state-machine walk and the stale-sentinel re-enable sequence you are eliminating).

## Why Fable for this task

Three coupled mechanisms — the `SCRAPING_ENABLED` config key, the `.enable-scraping` sentinel, and env-seeded security flags — interact across two processes with no shared memory. The fix collapses them to a single source of truth while preserving the no-restart enable path, surviving a one-release window where an old daemon may still expect the sentinel, and not reintroducing the exact stale-state bugs being fixed. The state machine must be *provably* simpler afterward, not just differently complicated.

## Background — the three bugs

1. **ARCH-2:** disable-scraping requires a daemon restart that is a no-op in Docker → UI shows "Archiving is paused" while jobs keep running. Worse: a stale `.enable-scraping` sentinel (written when the daemon was already enabled, hence never consumed) re-enables scraping on a later restart **against** `SCRAPING_ENABLED=false`.
2. **ARCH-3:** a `.trigger` left by a dead daemon 409-blocks all manual scrapes forever, and on restart causes a startup-run + trigger-run double scrape.
3. **SEC-2:** the RSS server reads `BIND_AUTH_ENABLED`/`BIND_IP_FILTER` from `os.environ`, seeded once at import — Settings-page changes to auth/IP-filtering **never take effect** until a manual RSS restart (`restart_daemon()` restarts only `bind.service`).

## Design (implement exactly this)

**Single source of truth = `config.env`, read live.** The daemon polls it per loop tick; the RSS server reads it per request through a small cache. The `.enable-scraping` sentinel is removed entirely. `.trigger` stays (it is an *event*, not *state*) but gets lifecycle hygiene.

### Task 1 — live-config helper (shared)

In `src/config_manager.py`, add a module-level `LiveConfig` helper (or equivalent function set):
- `get(key: str) -> str`: returns the effective value with precedence **process-start env > config.env > DEFAULTS**. "Process-start env" means: snapshot `os.environ` keys relevant to `DEFAULTS` **once at first use** — an operator-exported env var (Docker `environment:`, systemd `Environment=`) must keep winning forever (current contract), but values that were merely *seeded from config.env at startup* must not shadow later file edits. Implementation: the seeding sites (`src/bind.py:130-142`, `src/rss_server.py:136-143`) currently push config values INTO `os.environ` — **remove that seeding entirely** and route every consumer through `LiveConfig`; then "env wins" is simply "the var was present in `os.environ` at snapshot time". Audit ALL `os.getenv` call sites in `src/` for the managed keys (`SCRAPING_ENABLED`, `BIND_AUTH_ENABLED`, `BIND_IP_FILTER`, `SCRAPE_INTERVAL`, `ABB_URL`, `CIRCUIT_BREAKER_*`, `BIND_JOB_TIMEOUT`, `BIND_PROXY`, `BIND_PROXIES`, plus keys added by Waves 4-B/4-C if present) and migrate each one deliberately; list every migrated site in your summary. Keys NOT in `DEFAULTS` (e.g. `FLASK_SECRET_KEY`, `BIND_DB_PATH` handling at startup) stay on plain `os.getenv`.
- Cache by config-file `mtime_ns + size`: stat per call is fine (it's one syscall); re-parse only on change. Thread-safe enough for gunicorn sync workers (a lock around re-parse).
- **Constructor-injected path** so tests aim it at `tmp_path`.

### Task 2 — ARCH-2: daemon honors config live; sentinel removed

In `src/bind.py`:
1. Replace the boot-time `scraping_enabled = os.getenv(...)` with a per-tick `LiveConfig.get("SCRAPING_ENABLED")` check. Transitions:
   - false→true: schedule the job (as the sentinel path does today) and run immediately.
   - true→false: `schedule.clear()` (or cancel the specific job) — running jobs finish, no new ones start. Log both transitions.
2. Delete all `.enable-scraping` handling (`ENABLE_FILE`, `bind.py:220`, `:232-240`). **Startup cleanup:** unconditionally delete a leftover `.enable-scraping` AND a leftover `.trigger` before the first scheduled run (kills the stale-sentinel re-enable and the restart double-scrape in one stroke).
3. `SCRAPE_INTERVAL` stays start-time-only (re-scheduling intervals live is out of scope) — but note in a comment that it is intentionally not live.

In `src/rss_server.py`:
4. `api_scraping_enable` (`:557-577`): drop the sentinel touch and the `restart_daemon()` call — writing `SCRAPING_ENABLED=true` to config is now sufficient; the daemon picks it up within one tick. Message: "Scraping enabled. The daemon will start within a few seconds." **Rolling-upgrade window:** an old daemon won't see the change until restart. Mitigation: keep writing the sentinel for ONE release with a `# COMPAT(remove after vNEXT)` comment, since the new daemon deletes unknown sentinels at startup and ignores them at runtime — harmless to new, functional for old. The `restart_daemon()` call is removed now (it was already a no-op outside systemd, and on systemd the live-read makes it unnecessary).
5. `api_settings_post`: keep its existing `restart_daemon()` (other keys like `ABB_URL`/`SCRAPE_INTERVAL` still need a restart on systemd) but append to the success message which keys apply live vs. on-restart. Keep this honest and short.

### Task 3 — ARCH-3: trigger hygiene

In `api_trigger_scrape` (`src/rss_server.py:651-661`): if `.trigger` exists but its mtime is older than `2 × SCRAPE_INTERVAL` minutes (via `LiveConfig`), treat it as stale — overwrite (re-touch) and return 200 with a message noting a stale trigger was replaced, instead of 409. Fresh trigger → 409 as today. (Startup deletion was Task 2.2.)

### Task 4 — SEC-2: security flags read live

1. `requires_session_auth` (`src/rss_server.py:217-226`) and `check_ip_allowlist` (`src/security.py:482-496`) read `BIND_AUTH_ENABLED`/`BIND_IP_FILTER` through `LiveConfig` per request. Module-boundary note: `security.py` must not import `rss_server`; give `security.py` its own `LiveConfig` instance or inject it via `ip_allowlist_middleware(app, live_config)`.
2. Preserve the test contract: `tests/conftest.py` sets `BIND_AUTH_ENABLED=false` via `os.environ` **before import** — under the new precedence that is a process-start env var and still wins. Run the suite early to confirm; if any test monkeypatches `os.environ` *after* snapshot to flip auth, those tests reveal the snapshot semantics — fix the TESTS to monkeypatch `LiveConfig` (or use its injection point), and note each one. Do not weaken the precedence rule to make a test pass.

### Task 5 — loop extraction (TEST-3 enabler)

The main loop body (`bind.py:230-248`) is `# pragma: no cover` end to end. Extract one pure-ish function, e.g. `def loop_tick(ctx: DaemonContext) -> None` (dataclass holding store, scraper, live_config, schedule handle, state flags, data_dir), called from the `while` shell. The `pragma: no cover` shrinks to the `while`/`sleep` shell only. Unit-test `loop_tick` directly: trigger-file consumption, enable transition, disable transition, heartbeat write if Wave 5-A already landed (rebase carefully — coordinate the diff, don't duplicate state).

## Tests

Beyond the per-task tests above: a state-machine test enumerating (config-enabled × daemon-state × sentinel-present) and asserting the post-tick invariant **daemon-state == config value, no sentinel survives** — this is the proof the audit's ARCH-2 sequence can't recur.

## Constraints

- `SCRAPING_ENABLED` semantics in `config.env` are unchanged (format-compatible; no migration for users).
- CHANGELOG under `## [Unreleased]`: live enable/disable without restart; auth/IP-filter settings now apply within seconds; `.enable-scraping` deprecated (removed next release); stale-trigger recovery.
- Do not touch heartbeat code paths beyond mechanical merge (Wave 5-A owns them); do not touch shutdown/drain logic (Wave 5-C owns it).
- `docs/CONFIGURATION.md` + `docs/ARCHITECTURE.md`: update the control-flow descriptions (both currently describe the sentinel mechanism).

## Verification

```bash
source .venv/bin/activate
python -m pytest tests/ -q
ruff check src/ tests/ && ruff format --check src/ tests/
mypy src/
```

## Done criteria

Full suite green; the state-machine invariant test passes; grep shows zero remaining reads of the managed keys via bare `os.getenv` outside `LiveConfig` (except the documented startup-only ones); the ARCH-2 reproduction sequence (enable-while-enabled → disable → restart) can no longer re-enable scraping — covered by an explicit test.
