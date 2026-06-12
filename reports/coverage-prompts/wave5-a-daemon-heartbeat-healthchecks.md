# Wave 5-A — Daemon Heartbeat, Health Checks, Single-Container Supervision

**Model: Claude Fable**
**Dependencies:** none strictly; avoid running concurrently with Wave 5-B (both edit `src/bind.py`'s main loop region). Run 5-A before 5-B or vice versa, never together.
**Working directory:** `/Users/dante/Citadel/BIND`
**Activate the venv before any shell commands:** `source .venv/bin/activate`
**Findings remediated:** ARCH-1, DEP-2, DEP-6, ARCH-6 from `BIND_FULL_AUDIT_REPORT.md` (repo root — read all four in full first; ARCH-1 contains the candidate-evaluation table justifying the design below).

## Why Fable for this task

This is a coordinated daemon + RSS-server change with a rolling-upgrade compatibility window: old and new components must coexist for one release in every deployment mode (dual-container Docker, single-container Docker, systemd, unRAID). Getting the fallback semantics or the deployment-mode matrix wrong ships a status display that is *confidently* wrong instead of honestly unknown.

## Background

Daemon liveness is currently inferred from `logs/bind.log` mtime (`check_daemon_status`, `src/rss_server.py:259-278`). This is broken by construction in the **recommended** dual-container deployment: `bind-rss` has no `logs/` mount (`docker-compose.yml` shares only the `data` volume), so the status is permanently "unknown". The replacement channel is the one thing every deployment mode already shares: the WAL-mode SQLite database.

## Task 1 — heartbeat table (daemon side)

1. Add to `_SCHEMA_DDL` in `src/core/storage.py`:
   ```sql
   CREATE TABLE IF NOT EXISTS daemon_heartbeat (
       id           INTEGER PRIMARY KEY CHECK (id = 1),
       beat_at      TEXT    NOT NULL,          -- UTC ISO-8601
       state        TEXT    NOT NULL,          -- 'idle' | 'scraping' | 'disabled'
       interval_min INTEGER NOT NULL
   );
   ```
   Additive only — `CREATE TABLE IF NOT EXISTS` through the existing `_init_schema` path; no data migration. Do NOT touch `scrape_runs` (it is a job-granularity log; 30s beats would pollute the metrics page).
2. `MagnetStore` methods: `beat(state: str, interval_min: int) -> None` (single `INSERT OR REPLACE`) and `last_heartbeat() -> dict | None` (returns `beat_at`/`state`/`interval_min` or None).
3. Daemon main loop (`src/bind.py:230-248`): write a beat **throttled to every 30 seconds** (track last-beat monotonic time; the loop ticks at 1 Hz), and **immediately on state change**. States: `scraping` while a job future is running, `disabled` when `scraping_enabled` is false, else `idle`. Also beat once at startup before the first job so the UI flips promptly. Threading note: the beat is written from the **main thread**; the job runs in the executor thread on the same connection — finding ARCH-5 documents this pre-existing hazard and Wave 5-C fixes it; for now, write the beat via a short-lived `sqlite3.connect(db_path)` inside `beat()` (cheap at 30s cadence) to avoid widening the cross-thread window. Document this in a comment referencing ARCH-5.

## Task 2 — reader with fallback (RSS side)

Rewrite `check_daemon_status()`:
1. Read `last_heartbeat()`. If a row exists: `online` if `beat_at` is within 90 seconds, `offline` otherwise; if `state == 'disabled'`, report a distinct `("online", "Scraping disabled", ...)`-style status so the UI's paused banner and the status badge stop contradicting each other (keep the 3-tuple return shape and the existing status strings `online`/`offline`/`unknown` — the frontend `statusVariant` switch in `DashboardPage.tsx:122-126` and `endpoints.ts` types depend on them; put the disabled detail in the message string only).
2. **If no heartbeat row exists, fall back to the current mtime heuristic unchanged.** This is the rolling-upgrade window: a new RSS server against an old daemon must degrade to today's behavior, not report a dead daemon. Mark the fallback with a comment: "remove in the release after daemon heartbeat ships" — but do NOT remove it in this change.
3. Old RSS against new daemon needs nothing: it ignores the new table.

## Task 3 — DEP-2: health endpoints and container HEALTHCHECKs

1. Make `/health` (`src/rss_server.py:328-339`) DB-only: drop the `BindScraper().probe_target()` call and its 300s cache from this endpoint (a health probe must not depend on a third party's reachability or take 10s). Move the probe + cache to `/api/stats` as a `target_probe` field (it is operator-facing context, and `/api/stats` is already authenticated and polled). Keep `/health`'s response shape otherwise (`status`, `magnet_count`, `last_date`); add `daemon` with the Task-2 status string.
2. RSS container healthcheck — in `docker-compose.yml` under `bind-rss`, and `HEALTHCHECK` in `docker/Dockerfile.single`:
   `python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:5050/health', timeout=5).status==200 else 1)"` (the slim image has no curl/wget — verify before assuming; if curl exists, prefer `curl -fsS`).
3. Daemon container healthcheck — new module `src/healthcheck.py` runnable as `python -m src.healthcheck`: opens the DB read-only, exits 0 if the heartbeat is <90s old (or state `disabled` — a deliberately-paused daemon is healthy), 1 otherwise. Wire it as the `bind-daemon` healthcheck in compose with `start_period: 30s`.

## Task 4 — DEP-6 + ARCH-6: single-container entrypoint

Rewrite `docker/entrypoint.sh`:
1. **Supervision:** today the daemon is backgrounded with `&` and its death goes unnoticed. New behavior: start the daemon in the background, start gunicorn in the background, then `wait -n` on both; when either exits, kill the other and exit non-zero so Docker's restart policy recycles the pair. Mind the details: tini is PID 1 (signal forwarding is handled), but your script must propagate the kill to the survivor and preserve the failed child's exit code. Keep it POSIX-sh compatible if the base image's `/bin/sh` is dash — `wait -n` is bash-only; either switch the shebang to bash (verify bash exists in `python:3.11-slim` — it does) or use a polling loop. State the choice.
2. **ARCH-6 interval unification:** the script reads `${BIND_SCRAPE_INTERVAL:-60}` — a variable that exists nowhere else (the real key is `SCRAPE_INTERVAL`). Also `docker-compose.yml` hardcodes `--interval 60` in the `bind-daemon` command, which (Click: flag > envvar) silently overrides config. Fix both: entrypoint passes no `--interval` flag at all (let Click's `envvar="SCRAPE_INTERVAL"` + config seeding resolve it), and remove `--interval 60` from the compose command. Grep docs/unraid for `BIND_SCRAPE_INTERVAL` references and update.

## Tests

- Storage: `beat()`/`last_heartbeat()` round-trip; second `beat()` replaces, never duplicates (assert one row).
- RSS: `check_daemon_status` with fresh beat → online; stale beat → offline; `disabled` state → online + message; no row + log file present → mtime fallback engaged (monkeypatch as existing tests do); no row + no log → unknown.
- `/health` no longer calls `probe_target` (assert via monkeypatched scraper that raises if touched); `/api/stats` now carries `target_probe`.
- `python -m src.healthcheck` exit codes: 0 fresh / 0 disabled / 1 stale / 1 no-DB.
- Frontend type check still passes (`StatsData` gains `target_probe?` in `endpoints.ts` if you type it).

## Constraints

- Response-shape compatibility as specified in Task 2.1 — do not invent new status enum values.
- No edits to the scraping-control logic, sentinel files, or `SCRAPING_ENABLED` handling (Wave 5-B owns those). You will touch adjacent lines in the main loop; keep the diff surgical.
- CHANGELOG entry under `## [Unreleased]`: heartbeat table (schema addition), `/health` probe relocation (note: anyone scraping `target_probe` from `/health` must move to `/api/stats`), entrypoint supervision, interval-flag removal.

## Verification

```bash
source .venv/bin/activate
python -m pytest tests/ -q
ruff check src/ tests/ && mypy src/
docker compose config -q                      # compose file still valid
sh -n docker/entrypoint.sh || bash -n docker/entrypoint.sh
```

## Done criteria

Full suite green; dual-container status path no longer depends on `logs/`; a stopped daemon flips `/health`'s `daemon` field to offline within 90s (test via stale beat row); single-container design kills the pair when either process dies (reason through the script line by line in your summary — there is no docker runtime in this environment to integration-test it).
