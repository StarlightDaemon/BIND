# Wave 6-F — Dead Code Sweep & Version Reconciliation

**Model: 🔵 Claude Sonnet**
**Dependencies:** Wave 4-A committed (it already deletes `/api/dashboard`). Run this prompt LAST in the remediation program — it deletes code other prompts must not be touching mid-flight.
**Working directory:** `/Users/dante/Citadel/BIND`
**Activate the venv before any shell commands:** `source .venv/bin/activate`
**Findings remediated:** CQ-4, version skew (section 8.7 / Phase 4 of the audit), optional RES-3 from `BIND_FULL_AUDIT_REPORT.md`.

## Task 1 — CQ-4: dead-code deletions

For EVERY item: grep the whole repo (src, tests, docs, scripts, deployment) for references before deleting; delete dependent tests with their subjects; list each deletion + its reference-check result in your summary.

1. **Vesper-era server-rendered UI:** delete `src/templates/` (6 HTML files) and `src/static/css/`. No `render_template` call exists in `src/`. Then:
   - Remove `template_folder=...` from the `Flask(...)` constructor (`src/rss_server.py:85`).
   - Remove `app.jinja_env.globals["csrf_token"] = generate_csrf_token` (`:182`) — it served only those templates.
   - **Keep** `src/static/dist/` handling untouched (live SPA path).
2. **Basic-Auth path:** delete `requires_auth` and `check_auth` from `src/security.py` (`:504-563`) — no route uses them (verify again at runtime state, not just the audit's claim: `grep -rn "requires_auth\|check_auth" src/ tests/ docs/`). Delete their dedicated tests in `tests/test_security.py` (the `BIND_AUTH_ENABLED` *session*-auth tests stay — read carefully which decorator each test targets). Update the `CLAUDE.md` line mentioning `@requires_auth` to name `@requires_session_auth` instead.
3. **Form-channel CSRF:** with templates gone, no non-API POST surface exists. Simplify `csrf_protect` (`src/rss_server.py:200-207`) to validate the header on ALL POSTs (drop `_validate_csrf_form` and the path branch). Check the CSRF tests that POST to non-API paths (e.g. `client.post("/setup", data=...)` in `tests/test_rss_server.py:~442`) and update them to the header channel. NOTE: if Wave 4-C's cross-channel test landed, it asserts form-token-on-API → 403; that behavior is preserved by header-only validation — keep the test.
4. **Small items:**
   - `TrackerManager.get_default_trackers` (`src/core/tracker_manager.py:100-102`) — delete if grep confirms unused.
   - `ConfigManager.read_config`'s `print(...)` (`src/config_manager.py:101` region — locate by symbol; Wave 4-E refactored nearby) → `logger.warning`.
   - `frontend/src/api/endpoints.ts`: remove types orphaned by Wave 4-A's deletion if any remain (`DashboardData` — check usage in `DashboardPage.tsx` first; it may still be used as a local shape).
5. **Flat-file residue (do NOT delete data):** `data/magnets/` is operator data (migration source). Only action: add a note to `docs/CLEANUP_GUIDE.md` that post-migration archives can be removed manually, referencing `src/core/migrate.py`'s "flat files are untouched" contract.

## Task 2 — version reconciliation

`pyproject.toml` says `2.2.0`; `CHANGELOG.md` documents through `1.2.1`. The docker-publish workflow derives image tags from git tags, so this skew will eventually mint a misleading image version.

1. Decide by evidence: `git log --oneline v1.2.1..HEAD 2>/dev/null || git tag -l` — what shipped since 1.2.1? The React/Fujin UI migration, SQLite storage (if post-1.2.1), and this remediation program are substantial. Recommended resolution: set version to **1.3.0** and write the missing CHANGELOG section for everything between 1.2.1 and now (summarize from git log + the `## [Unreleased]` entries earlier waves accumulated — fold them in). If git history shows the 2.x numbering was deliberate (look for a commit message explaining it), keep 2.2.0 and backfill the CHANGELOG instead. State which you found.
2. Whichever number wins: `pyproject.toml`, `CHANGELOG.md` heading with today's date, and grep docs for stale version strings (`grep -rn "2\.2\.0\|1\.2\.1" docs/ README.md` — update only where it names the *current* version, not historical records).

## Task 3 — RES-3 (optional, small): drift-aware fetch gating

Only if the diff stays small (~20 lines + test): in `BindScraper`, when `SchemaHealthMonitor` has fired its CRITICAL within the current job, skip remaining detail-page fetches for that job (the RSS fetch next cycle is the recovery probe). Add `SchemaHealthMonitor.is_drifted() -> bool` (read current state, no behavior change to recording) and consult it in the `run_job` book loop — note `run_job` lives in `src/bind.py` and the monitor on the scraper; expose via `scraper.schema_monitor.is_drifted()`. One test: monitor in drifted state → subsequent books are skipped with a single warning log. If this turns out invasive after Waves 4/5's changes, SKIP it and say so — it is explicitly optional.

## Constraints

- Pure-deletion discipline: Tasks 1's diffs should be ~entirely red. Any green lines beyond the csrf_protect simplification and logger swap need justification.
- Full suite green after EACH task (run between tasks, not just at the end — a deletion that breaks tests must be caught at its own step).
- Coverage gate: deleting tested-dead-code shifts the coverage denominator — confirm `--cov-fail-under=75` still passes (it will; coverage should *rise*).

## Verification

```bash
source .venv/bin/activate
python -m pytest tests/ -q
ruff check src/ tests/ && ruff format --check src/ tests/
mypy src/
cd frontend && npx tsc --noEmit && cd ..
grep -rn "render_template\|requires_auth\|_validate_csrf_form\|get_default_trackers" src/ && echo "LEFTOVERS FOUND" || echo "clean"
```

## Done criteria

Templates/CSS/Basic-Auth/form-CSRF gone with zero dangling references; version + CHANGELOG reconciled with the `[Unreleased]` entries folded in; suite green; summary lists every deletion with its grep evidence and the version decision rationale.
