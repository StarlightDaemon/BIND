# Wave 4-C — Session & Credential Hardening

**Model: Claude Opus**
**No dependencies** — runs independently. Avoid running concurrently with Wave 4-B (both edit `src/security.py`).
**Working directory:** `/Users/dante/Citadel/BIND`
**Activate the venv before any shell commands:** `source .venv/bin/activate`
**Findings remediated:** SEC-6, SEC-7, SEC-8, SEC-9, TEST-2 from `BIND_FULL_AUDIT_REPORT.md` (repo root — read them in full first).

## Why Opus for this task

Three of the five items are footguns: module-import-time reordering in `rss_server.py` (a mistake invalidates every session or splits keys across gunicorn workers), a credentials schema migration (v2 → v3) that must not reset lockout state, and a file-locking change where the wrong lock scope silently reintroduces the lost-update race.

## Task 1 — SEC-6: secret-key resolution order, ephemeral severity, Secure cookie

Current bug: `app.secret_key` is resolved at `src/rss_server.py:119-121` using `BIND_DB_PATH` from the environment, **before** `config.env` is loaded into the environment at lines 136-143. A `BIND_DB_PATH` set only in config.env puts the key file in the wrong data dir.

1. Move the config-load block (`try: _config_mgr = ConfigManager() ... except`) **above** the secret-key resolution. Audit every statement between the current positions for ordering sensitivity before moving (`_build_frontend()` and `app = Flask(...)` must stay first; the security-headers hook and cookie config don't care). State in your summary exactly which statements moved and why nothing else could break.
2. In `_resolve_secret_key` (`src/rss_server.py:88-116`): escalate the ephemeral-fallback log from `logger.warning` to `logger.critical`, and extend the message to say sessions will break across gunicorn workers (each worker generates its own key).
3. Add `SESSION_COOKIE_SECURE` support: new key `BIND_COOKIE_SECURE` (boolean, default `false`), read the same way the other booleans are. Add to `ConfigManager.DEFAULTS` + `VALIDATORS` (`boolean`). Do not add to the Settings UI. Apply via `app.config["SESSION_COOKIE_SECURE"]` at startup. Document in `docs/CONFIGURATION.md` (recommend `true` for anyone fronting BIND with TLS/Cloudflare Tunnel).
   - **Clobber caution:** `api_settings_post` (`src/rss_server.py:533-545`) builds its payload from a fixed dict, and `write_config` emits every `DEFAULTS` key — carry `BIND_COOKIE_SECURE` through from `read_config()` in that route so a UI save cannot reset it (see finding ARCH-4 for the failure shape).

## Task 2 — SEC-7: per-IP lockout (credentials schema v3) + atomic read-modify-write

Current bugs: (a) five wrong passwords from *any* IP lock the single account globally — an unauthenticated remote DoS; (b) `record_failed_login`/`record_successful_login` (`src/security.py:326-368`) do read → modify → write with locks held only during the individual read and write — concurrent gunicorn workers lose updates.

1. **Schema v3.** Bump `CREDENTIALS_VERSION` to 3. New field `failed_by_ip: dict[str, {"count": int, "locked_until": str|null}]`. Keep the existing global `failed_attempts`/`locked_until` as a ceiling: global lockout triggers at a higher threshold (suggested: 5× `MAX_FAILED_ATTEMPTS` = 25 total failures across all IPs) so a distributed attack is still stopped. Per-IP lockout keeps today's semantics (5 failures → 15 min) but only for that source IP.
2. **Migration.** Extend `_migrate_credentials` (`src/security.py:159-175`): v2 → v3 adds `failed_by_ip: {}` and **preserves** existing `failed_attempts`/`locked_until` untouched (the audit specifically verified no path resets lockout state — keep it that way). Migration must be idempotent.
3. **Lock scope.** Rewrite the read-modify-write sites to hold `fcntl.LOCK_EX` across the full cycle: open `r+`, lock, read, mutate, `seek(0)`, write, `truncate()`, unlock. Apply to `record_failed_login`, `record_successful_login`, and the lockout-expiry clear inside `is_account_locked` (`src/security.py:317-321`). Factor a `_locked_update(mutator: Callable[[dict], dict]) -> bool` helper rather than triplicating the pattern.
4. **API changes ripple.** `is_account_locked()` and `verify_credentials()` need the client IP to evaluate per-IP state — thread it through from the callers (`src/rss_server.py:357`, `src/security.py:511-517`). Check every call site, including tests.
5. Prune stale per-IP entries (expired lockout + zero count) during writes so the file doesn't grow unboundedly.
6. `record_successful_login` from an IP clears that IP's entry and the global counter (successful auth proves the credential; keeping other IPs' counters is acceptable either way — pick one and document it).

## Task 3 — SEC-8: CSRF comparison + rotation

1. Replace both `!=` token comparisons with `hmac.compare_digest` (`src/rss_server.py:171`, `:178`). Guard for `None` before comparing (compare_digest raises on None).
2. Rotate the CSRF token on successful login: in `api_login` after `session["authenticated"] = True`, do `session.pop("csrf_token", None)` then `generate_csrf_token()`.
3. Frontend counterpart: in `frontend/src/context/AuthContext.tsx`, call `invalidateCsrf()` after a successful `login(...)` (it is already imported there for logout) so the client refetches instead of failing one request.

## Task 4 — SEC-9: session fixation hygiene

In `api_login`, on successful verification call `session.clear()` **before** setting `authenticated` and re-issuing the CSRF token (order matters: clear → mark authenticated → generate token).

## Task 5 — TEST-2: CSRF binding-depth tests

Append to `tests/test_rss_server.py` (do not modify existing tests):
1. **Cross-channel:** a POST to an `/api/` route with the valid token supplied only as a *form field* (not the `X-CSRF-Token` header) → 403.
2. **Cross-session:** obtain a token in client A's session; send it from a fresh client B → 403.
3. **Rotation:** token before login ≠ token after successful login.

Also add tests for Tasks 1-2 in the appropriate files: per-IP lockout (IP x locked, IP y still allowed), global ceiling, v2→v3 migration preserving an active lockout, and concurrent-update integrity (two interleaved `record_failed_login` calls via threads against a tmp_path credentials file → final count == 2). Remember the project rule: monkeypatch `src.security.CREDENTIALS_FILE` to `tmp_path` in any test touching credential functions.

## Constraints

- Files in scope: `src/rss_server.py`, `src/security.py`, `src/config_manager.py`, `frontend/src/context/AuthContext.tsx`, `docs/CONFIGURATION.md`, tests.
- Do not change the password policy, hash algorithm, or `save_credentials` validation.
- The v3 file written by new code must still be readable if the operator rolls back to v2 code (v2 ignores unknown fields — verify `load_credentials` tolerance rather than assuming).

## Verification

```bash
source .venv/bin/activate
python -m pytest tests/test_security.py tests/test_security_core.py tests/test_rss_server.py -q
python -m pytest tests/ -q
ruff check src/ tests/ && mypy src/
cd frontend && npx tsc --noEmit && cd ..
```

## Done criteria

Full suite green; the concurrency test fails against the pre-change code (verify once by stashing); a v2 credentials file with an active lockout migrates to v3 still locked; login rotates both session and CSRF token.
