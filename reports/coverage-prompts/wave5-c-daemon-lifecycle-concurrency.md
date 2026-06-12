# Wave 5-C — Daemon Lifecycle: Bounded Drain & Thread-Safe Telemetry

**Model: Claude Opus**
**Dependencies:** Wave 5-B **committed** (both rewrite regions of `src/bind.py`; 5-B restructures the loop this change hooks into). Wave 5-A should also be committed if it has been scheduled (heartbeat code is adjacent).
**Working directory:** `/Users/dante/Citadel/BIND`
**Activate the venv before any shell commands:** `source .venv/bin/activate`
**Findings remediated:** RES-4, ARCH-5 from `BIND_FULL_AUDIT_REPORT.md` (repo root — read both in full first).

## Why Opus for this task

Signal handlers, non-daemon `ThreadPoolExecutor` atexit-join semantics, `os._exit` placement, and cross-thread SQLite connection sharing — each is a place where plausible-looking code deadlocks or corrupts under exactly the conditions it exists to handle. The shutdown matrix below must be reasoned through, not pattern-matched.

## Bug 1 — RES-4: shutdown is unbounded after a job timeout, and both supervisors SIGKILL mid-job

Current behavior (`src/bind.py`):
- SIGTERM sets a flag; the main thread is usually blocked in `future.result(timeout=JOB_TIMEOUT)` and drains until job-end or timeout — bounded, OK.
- **After** a timeout, the abandoned job thread keeps running. On `sys.exit(0)`, Python's atexit joins the non-daemon executor thread **unconditionally** — a hung network call blocks exit forever. There is no hard-shutdown path.
- Supervisor reality: `deployment/bind.service` has no `TimeoutStopSec` (systemd default 90s → SIGKILL whenever the drain exceeds 90s); `docker-compose.yml` has no `stop_grace_period` (Docker default 10s → effectively every active-job stop is a SIGKILL).

### Required behavior

1. **Bounded drain:** on SIGTERM/SIGINT, wait at most `BIND_DRAIN_TIMEOUT` (env, default **60s**) for the current job — not the full remaining `BIND_JOB_TIMEOUT`. Design constraint: the signal arrives *while* the main thread sits in `future.result(timeout=JOB_TIMEOUT)`; the handler can only set the flag. Restructure the wait into a loop of short `future.result(timeout=1)` slices (or `concurrent.futures.wait` with 1s timeouts) inside `run_job_with_timeout`, accumulating against both deadlines: `JOB_TIMEOUT` (job too long → record `timeout` run as today) and, once shutdown is requested, `BIND_DRAIN_TIMEOUT` from the moment of the signal. Preserve the exact `scrape_runs` recording semantics for the existing result kinds — `success`/`empty`/`failure`/`timeout` (CHECK constraint, `src/core/storage.py:20` — do NOT add a new result kind; a drain-abandoned job records `timeout`).
2. **Hard exit path:** after the loop exits, call `_job_executor.shutdown(wait=False, cancel_futures=True)`; if the job future is still not done after that, log a warning and `os._exit(0)` — never let atexit join a hung thread. Flush logging handlers before `os._exit` (it skips atexit and buffered I/O). When the future *is* done, exit normally via the existing path.
3. **Supervisor budgets:** add `TimeoutStopSec=120` to `deployment/bind.service` and `stop_grace_period: 75s` to `bind-daemon` in `docker-compose.yml` (budget = drain 60s + margin; SIGKILL becomes the backstop, not the norm). CHANGELOG note for systemd installs (service-file change requires `systemctl daemon-reload`).

## Bug 2 — ARCH-5: cross-thread use of one SQLite connection

After a job timeout, the main thread calls `store.record_scrape_run(...)` (`bind.py` finally-block) **while the executor thread is still inside `run_job`** using the same `check_same_thread=False` connection — two threads, one connection, autocommit. Python's serialized sqlite3 mode currently masks it.

### Required behavior

Make `record_scrape_run` thread-safe without restructuring `MagnetStore`'s single-connection design for readers: open a short-lived `sqlite3.connect(self.db_path)` inside `record_scrape_run` (and inside `beat()` if Wave 5-A landed it with a TODO referencing this finding — check and consolidate). The write is rare (once per job / per 30s), so per-call connections are free; WAL + `busy_timeout` handle the cross-connection contention. Alternative designs (thread-local connection map, moving recording into the job thread) are acceptable ONLY if you justify why they're strictly better here — the default is the short-lived connection.

## Tests (append; do not modify existing tests except where 5-B's restructuring already moved them)

With `time.sleep`/timeouts shrunk via monkeypatched constants — no real multi-second waits in the suite:
1. Drain bounded: a job thread blocked on an `threading.Event` + shutdown flag set → `run_job_with_timeout` returns within the (shrunk) drain budget and records `timeout`.
2. Job-timeout path unchanged: no shutdown flag → full `JOB_TIMEOUT` honored, `timeout` recorded with partial `items_new` (existing test `test_records_scrape_run_on_timeout` must still pass).
3. Hard exit: with the future still running post-loop, assert `shutdown(wait=False, cancel_futures=True)` is invoked and the `os._exit` branch is reached (monkeypatch `os._exit` to record the call — never actually exit pytest).
4. Concurrency: `record_scrape_run` called from a second thread while the main `_conn` is mid-transaction in the first → both writes land (assert row count), no exception.
5. Signal semantics: existing signal-handler tests in `tests/test_bind_daemon.py` pass unmodified.

## Constraints

- Files in scope: `src/bind.py`, `src/core/storage.py`, `deployment/bind.service`, `docker-compose.yml`, `tests/test_bind_daemon.py`, `tests/test_storage*.py`, CHANGELOG.
- Do not change scheduling, sentinel, or live-config logic (Wave 5-B owns those); do not touch the RSS server.
- `BIND_DRAIN_TIMEOUT` is env-only (no ConfigManager/UI exposure); document it in `docs/CONFIGURATION.md`'s env-var section.

## Verification

```bash
source .venv/bin/activate
python -m pytest tests/test_bind_daemon.py tests/test_storage.py tests/test_storage_extended.py -q
python -m pytest tests/ -q
ruff check src/ tests/ && mypy src/
python -c "import configparser"  # sanity; then validate the unit file:
systemd-analyze verify deployment/bind.service 2>/dev/null || echo "no systemd on macOS — review unit syntax manually"
docker compose config -q
```

## Done criteria

Full suite green; the four shutdown scenarios (idle stop, mid-job stop, post-timeout stop with hung thread, SIGINT during drain) are each either tested or explicitly walked through in your summary with line references; `scrape_runs` CHECK constraint untouched.
