# Wave 4-A — Phase-1 Security Mechanics

**Model: 🔵 Claude Sonnet**
**No dependencies** — runs independently. Run this prompt FIRST among Wave 4 (it deletes a route other prompts must not touch).
**Working directory:** `/Users/dante/Citadel/BIND`
**Activate the venv before any shell commands:** `source .venv/bin/activate`
**Findings remediated:** SEC-1, SEC-4/DEP-1, SEC-5, CQ-3, TEST-1 from `BIND_FULL_AUDIT_REPORT.md` (repo root — read those five findings in full before starting).

## Context

BIND is a Python/Flask homelab daemon that scrapes AudioBookBay, stores magnet hashes in SQLite, and serves an RSS feed + React SPA. A full audit identified five mechanical security fixes. All specs below are exact — do not redesign, just implement. Line numbers were correct at audit time; if they have drifted, locate by symbol name.

## Task 1 — SEC-1: close the unauthenticated data routes

1. **Delete** the `/api/dashboard` route (`api_dashboard`, `src/rss_server.py:420-435`). It is dead code — the frontend uses `/api/stats`.
2. **Delete** the `dashboard.get` client binding and `DashboardData` usages it orphans in `frontend/src/api/endpoints.ts` (the `DashboardData` interface stays if `DashboardPage.tsx` still references the type — check; the page constructs a `DashboardData`-shaped object from `StatsData`, so keep the type, delete only the `get` entry).
3. Add `@requires_session_auth` to `api_magnets` (`src/rss_server.py:438`).
4. Add a CHANGELOG entry under an `## [Unreleased]` heading noting both public-API changes.
5. In `docs/CONFIGURATION.md`, add a short subsection stating that `/feed.xml` is intentionally unauthenticated (RSS consumers cannot do session auth) and is protected only by the IP allowlist.

## Task 2 — SEC-4/DEP-1: Docker build-context hygiene

1. Create `.dockerignore` at repo root containing at minimum:
   ```
   data/
   logs/
   credentials.json
   .git/
   .github/
   tests/
   docs/
   reports/
   audit-reports/
   .raiden/
   frontend/node_modules/
   **/__pycache__
   *.log
   .pytest_cache/
   .ruff_cache/
   .venv/
   src/static/dist/
   ```
   Note: `src/static/dist/` must stay ignored — the Dockerfiles build the frontend in a dedicated stage and `COPY --from=frontend-builder`; the local dist must not leak in via `COPY . .`. Verify the two Dockerfiles still produce a working image conceptually (the frontend stage provides dist).
2. Delete the stale `credentials.json` at the repo root (it is gitignored, contains a real scrypt hash, and is a leftover from a pre-`data/` layout — the live file is `data/credentials.json`).
3. Run `chmod 600 data/.secret_key` (current mode is 0666 — a WSL→macOS migration artifact).

## Task 3 — SEC-5: security-log event coverage

Using the existing `log_security_event()` (`src/security.py:81`), add events at these sites:
- `CSRF_FAILED` — in `_validate_csrf_form` and `_validate_csrf_json` (`src/rss_server.py:168-179`) before the `abort(403)`. Include the request path in the details field. Username field: `"-"`.
- `IP_BLOCKED` — in `check_ip_allowlist` (`src/security.py:482-496`) before returning the 403. **Rate-limit to one log line per IP per 60 seconds** (module-level `dict[str, float]` of last-logged monotonic timestamps is sufficient; no persistence needed) so a scanner cannot churn the 1000-line rotation window.
- `SETUP_REJECTED` — in `api_setup` when setup is already complete (`src/rss_server.py:393-394`).
- `LOGOUT` — in `api_logout` (`src/rss_server.py:364-367`), only when the session was actually authenticated.
- `ACCOUNT_UNLOCKED` — in `is_account_locked` on the lockout-expiry branch (`src/security.py:317-321`).

Update the docstring event list in `log_security_event`.

## Task 4 — CQ-3: redact proxy credentials in logs

Add a small helper (suggested home: `src/core/egress_manager.py`):

```python
def redact_proxy(url: str) -> str:
    """Strip user:pass@ from a proxy URL for safe logging."""
```

Use it in `ProxyPool.mark_failed` (`src/core/egress_manager.py:45`). Also remove (or reduce to key names only) the env-vs-file value logging in `src/bind.py:139` — it can print `BIND_PROXY` values containing credentials.

## Task 5 — TEST-1: auth-enforcement matrix test

Add a new test module `tests/test_auth_matrix.py`:

1. A module-level literal list `PROTECTED_ROUTES` of `(method, path, needs_json_body)` covering every session-protected endpoint: `/api/stats`, `/api/metrics`, `/api/settings` (GET and POST), `/api/scraping/enable`, `/api/settings/trackers`, `/api/settings/password`, `/api/logs`, `/api/trigger-scrape`, and (after Task 1) `/api/magnets`.
2. Parametrized test: with `monkeypatch.setenv("BIND_AUTH_ENABLED", "true")` and no session → assert **401** for each. (POSTs need a valid CSRF token in the session + header first — copy the `session_transaction` pattern from `tests/test_rss_server.py:544-624` — otherwise you'll assert on the 403 CSRF rejection instead.)
3. Parametrized test: same routes with `sess["authenticated"] = True` → assert status is **not 401** (200/400/409/500 are all acceptable — we only assert the guard passed).
4. **Meta-assertion**: iterate `app.url_map.iter_rules()`, take every rule starting with `/api/`, subtract an explicit literal `PUBLIC_API_ROUTES` allowlist (`/api/login`, `/api/logout`, `/api/me`, `/api/csrf-token`, `/api/setup`, `/api/setup/status`), and assert the remainder equals the path set of `PROTECTED_ROUTES`. This makes the test fail loudly when a new route is added without classification.

Do NOT modify `tests/conftest.py` or existing tests.

## Verification

```bash
source .venv/bin/activate
python -m pytest tests/ -q                 # full suite green
ruff check src/ tests/ && ruff format --check src/ tests/
mypy src/
cd frontend && npx tsc --noEmit && cd ..   # endpoints.ts edit compiles
ls -la data/.secret_key                    # mode 600
test ! -f credentials.json && echo "root credentials.json gone"
```

## Done criteria

- `/api/dashboard` no longer exists; `GET /api/magnets` returns 401 when auth is enabled and no session is present.
- `.dockerignore` present; stale root `credentials.json` deleted; `.secret_key` mode 0600.
- All five new event types appear in `security.log` when triggered (spot-check `CSRF_FAILED` via a test).
- No proxy URL with embedded credentials can reach a log line.
- `tests/test_auth_matrix.py` passes and its meta-assertion enumerates the live route map.
