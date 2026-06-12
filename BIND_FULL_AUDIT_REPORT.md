# BIND Full Audit Report

**Date:** 2026-06-12
**Repository:** `/Users/dante/Citadel/BIND`
**Scope:** Full read of `src/` and `frontend/src/`; test-suite skim; deployment artifacts; dependency review. Builds on the structural audit `reports/BIND_REPOSITORY_AUDIT_2026-06-12.md` (Section 9 items accepted as confirmed).
**Codebase state:** branch `main`, pyproject version 2.2.0, CHANGELOG at 1.2.1.

---

## Executive Summary

| Severity | Count |
|---|---|
| Critical | 0 |
| High | 6 |
| Medium | 15 |
| Low | 13 |
| Informational | 8 |

No remotely exploitable critical vulnerability was found: SQL is parameterized end-to-end, the RSS XML output is correctly escaped, React never bypasses its escaping, and CSRF covers every state-mutating route. The High findings are instead about **security controls that silently fail to apply** and **observability that is broken in the recommended deployment**.

**Top 5 findings in plain language:**

1. **Saving security settings in the UI does nothing.** The web server reads `BIND_AUTH_ENABLED` and `BIND_IP_FILTER` from environment variables seeded once at process start; the Settings page writes `config.env` and restarts only the *daemon*. Turning authentication on (or off) in the UI never takes effect on the web server until someone manually restarts it. In Docker, even the daemon restart is a no-op. (SEC-2)
2. **The IP allowlist — the only guard on the public data routes — breaks under the intended reverse-proxy ingress.** Behind a loopback proxy (Cloudflare Tunnel → nginx → gunicorn), the *first* entry of `X-Forwarded-For` is trusted, which is attacker-controlled; behind a containerized proxy, every visitor appears to come from a private IP and the allowlist passes everyone. (SEC-3)
3. **Daemon status is permanently "unknown" in the recommended dual-container deployment.** The status heuristic reads `logs/bind.log` mtime, but the `bind-rss` container has no logs mount, so the file never exists there. Replace with a heartbeat row in the shared SQLite database. (ARCH-1)
4. **There is no `.dockerignore`.** `COPY . .` bakes the local `data/` directory (live SQLite DB, `.secret_key`), `logs/`, a stale `credentials.json`, and `.git` into locally built images; CI-published images carry `.git`, tests, and docs. (DEP-1)
5. **The retry engine's transient-network-error branch is dead code in production.** It tests `isinstance(e, (ConnectionError, TimeoutError))` against Python *builtins*, which neither `curl_cffi` nor `requests`/`cloudscraper` exceptions subclass. Connection failures and timeouts skip in-layer retries entirely. Tests pass because they raise builtins. (RES-2)

A sixth point worth calling out: effective auth coverage in the test suite is near zero despite 97.5% line coverage, because `conftest.py` disables auth globally and only one route is ever exercised with auth enabled. (TEST-1)

---

## Security

### **[HIGH] SEC-1 — `/api/dashboard` and `/api/magnets` expose torrent data without session auth; `/api/dashboard` is dead code**

**Diagnosis.** Three routes return magnet data without authentication: `/feed.xml` (intentional — RSS consumers can't do session auth), `/api/magnets` ([rss_server.py:438](src/rss_server.py:438)), and `/api/dashboard` ([rss_server.py:420](src/rss_server.py:420)). Meanwhile `/api/stats` ([rss_server.py:461](src/rss_server.py:461)) returns the *same* recent-magnets payload but requires session auth — the inconsistency indicates oversight, not design. Verdict on intent: **oversight**. Evidence: the React dashboard actually calls the authenticated `dashboard.stats()` ([DashboardPage.tsx:66](frontend/src/pages/DashboardPage.tsx:66)); `/api/dashboard` is defined in [endpoints.ts:129](frontend/src/api/endpoints.ts:129) but **never invoked by any page** — it is an unused, unauthenticated duplicate of an authenticated endpoint, left from the React migration (commit `e51e93f`). `/api/dashboard` additionally leaks operational state (daemon online/offline) to unauthenticated callers.

**Exposure.** On the trust path it's gated only by the IP allowlist — which SEC-3 shows is bypassable or void in common ingress configurations. An unauthenticated caller can then enumerate the entire magnet collection via `/api/magnets?page=N`.

**Resolution.**
1. Delete the `/api/dashboard` route and the `dashboard.get` client binding (it is unused).
2. Add `@requires_session_auth` to `/api/magnets`.
3. Keep `/feed.xml` public but document the decision in `docs/CONFIGURATION.md`; optionally add a `?token=` feed key (the old self-audit's "API Auth" recommendation) for users who expose BIND through a tunnel.

**Migration flag:** YES — public API surface change (`/api/dashboard` removal, `/api/magnets` auth). Feed consumers are unaffected.

### **[HIGH] SEC-2 — `BIND_AUTH_ENABLED` / `BIND_IP_FILTER` changes saved via the UI never apply to the RSS server**

**Diagnosis.** The RSS server seeds `config.env` values into `os.environ` once at import ([rss_server.py:136-143](src/rss_server.py:136)). The auth decorator and IP middleware read `os.getenv(...)` per request ([rss_server.py:220](src/rss_server.py:220), [security.py:484](src/security.py:484)) — but the environment is never refreshed. `POST /api/settings` writes `config.env` and calls `restart_daemon()`, which restarts **only `bind.service`** ([config_manager.py:249-254](src/config_manager.py:249)), never `bind-rss.service`. In Docker there is no systemctl at all, so nothing restarts. Net effect: a user who flips Authentication or IP Filter in the Access & Security tab ([SettingsPage.tsx:177-191](frontend/src/pages/SettingsPage.tsx:177)) gets a success toast ("Configuration saved. Daemon restarted successfully.") while the web server continues enforcing the *old* values indefinitely. The dangerous direction: an operator who believes they have *enabled* auth is running an open panel.

**Resolution.** Read these flags from `ConfigManager` at request time instead of `os.environ` (the config read is an flock'd file read; cache it with a short TTL or an mtime check to keep per-request cost near zero). Env vars should still win when explicitly set — preserve precedence by checking `os.environ` first only for keys that were present at process start. Alternatively (smaller change, worse UX): have `/api/settings` report honestly that web-server-side settings require a `bind-rss` restart.

**Migration flag:** NO (behavioral fix; config format unchanged).

### **[HIGH] SEC-3 — XFF trust model breaks under the intended ingress paths**

**Diagnosis.** `get_client_ip()` ([security.py:454-472](src/security.py:454)) trusts `X-Forwarded-For` only when the TCP peer is loopback, then takes the **first** element ([security.py:471](src/security.py:471)). Two failure modes:

1. **Loopback proxy (the stated Cloudflare Tunnel → nginx → gunicorn path):** nginx's standard `$proxy_add_x_forwarded_for` *appends* to whatever XFF the client sent, and Cloudflare likewise appends. The first element is therefore **attacker-supplied**. An external attacker sends `X-Forwarded-For: 192.168.1.10` → `get_client_ip()` returns a private address → `is_ip_allowed()` passes → IP allowlist bypassed for `/feed.xml`, `/api/magnets`, login attempts; security-log entries and lockout records carry the forged IP.
2. **Containerized proxy (proxy in another container / Docker network, or Docker's userland proxy):** the TCP peer is the proxy's RFC-1918 address — not loopback — so XFF is ignored *and* every external visitor is evaluated as that private proxy IP. The allowlist passes **everyone**, and all audit-log entries record the proxy IP. The trust model silently inverts from fail-closed to fail-open.

**Resolution.** Replace first-element parsing with rightmost-untrusted parsing: walk the XFF chain from the right, skipping addresses inside a configurable trusted-proxy set, and return the first untrusted hop. Add a `BIND_TRUSTED_PROXIES` config key (comma-separated CIDRs, default `127.0.0.1/32,::1/128` — current behavior preserved). Document that when fronted by Cloudflare, `CF-Connecting-IP` is the more reliable header. Werkzeug's `ProxyFix` with `x_for` depth is an acceptable off-the-shelf alternative if a fixed hop count is documented per deployment.

**Migration flag:** YES — new config key `BIND_TRUSTED_PROXIES` (backward-compatible default).

### **[HIGH] SEC-4 — No `.dockerignore`: secrets and repo internals baked into image layers**

**Diagnosis.** Both [Dockerfile](Dockerfile) and [docker/Dockerfile.single](docker/Dockerfile.single) run `COPY . .` and there is **no `.dockerignore`** in the repo. Consequences:
- **Local builds** (the documented `docker compose up --build` path) copy `data/` — including the live `bind.db` and `data/.secret_key` — plus `logs/`, and the stale root `credentials.json` (a real scrypt hash; see SEC-11) into an image layer. Anyone who can pull or export that image recovers the Flask signing key (full session forgery) and the password hash.
- **CI-published images** (`docker-publish.yml` → `starlightdaemon/bind` on Docker Hub) are built from a clean checkout, so no runtime secrets — but they still ship `.git/` (full history), `tests/`, `docs/`, `.raiden/`, inflating the image and its CVE/exposure surface.

Verified not-in-git: `git ls-files` shows no credentials/db/log files tracked, and `.gitignore` covers `data/` and `credentials.json` — the exposure is exclusively via the Docker build context.

**Resolution.** Add `.dockerignore` containing at minimum: `data/`, `logs/`, `credentials.json`, `.git/`, `.github/`, `tests/`, `docs/`, `reports/`, `audit-reports/`, `.raiden/`, `frontend/node_modules/`, `**/__pycache__`, `*.log`, `.pytest_cache/`, `.ruff_cache/`. Rotate `data/.secret_key` and treat any locally built/pushed image as compromised.

**Migration flag:** NO.

### **[MEDIUM] SEC-5 — Security log misses auth-relevant events**

**Diagnosis.** Six event types are logged ([security.py:81-107](src/security.py:81)): `ACCOUNT_CREATED`, `LOGIN_SUCCESS`, `LOGIN_FAILED`, `ACCOUNT_LOCKED`, `PASSWORD_CHANGED`, `PASSWORD_CHANGE_FAILED`. Not logged anywhere:
- **CSRF validation failures** — `_validate_csrf_form/_json` just `abort(403)` ([rss_server.py:168-179](src/rss_server.py:168)). A CSRF probe campaign is invisible.
- **IP allowlist rejections** — the 403 in [security.py:489-494](src/security.py:489) is silent. You cannot see who is knocking.
- **Setup endpoint access after setup is complete** — `POST /api/setup` returns 400 silently ([rss_server.py:393-394](src/rss_server.py:393)); repeated attempts are a takeover probe signal.
- **Logout** ([rss_server.py:364-367](src/rss_server.py:364)) and **lockout expiry/auto-unlock** ([security.py:317-321](src/security.py:317)) — useful for session-timeline reconstruction.

**Resolution.** Add `CSRF_FAILED`, `IP_BLOCKED`, `SETUP_REJECTED`, `LOGOUT`, `ACCOUNT_UNLOCKED` events through the existing `log_security_event()`. Rate-limit `IP_BLOCKED` writes (one per IP per minute) so a scanner can't churn the 1000-line rotation window and erase older evidence — that rotation cap itself is worth raising for the same reason.

**Migration flag:** NO.

### **[MEDIUM] SEC-6 — Secret-key resolution: ordering bug, multi-worker ephemeral split, missing `Secure` cookie flag**

**Diagnosis.** The resolution chain (env → `data/.secret_key` → ephemeral, [rss_server.py:88-121](src/rss_server.py:88)) is sound per deployment mode: systemd and both Docker modes persist the key on the data volume with `chmod 0600`, and `unraid/bind.xml` documents `FLASK_SECRET_KEY` with no committed default. Three defects remain:

1. **Ordering:** the key is resolved at [rss_server.py:119-121](src/rss_server.py:119) *before* `config.env` is loaded into the environment at [rss_server.py:136-143](src/rss_server.py:136). A `BIND_DB_PATH` set only in `config.env` (not env) means the key file lands in `./data` while the DB lives elsewhere — two hosts sharing a config can end up with divergent keys.
2. **Ephemeral mode under gunicorn:** if the data dir is unwritable, **each of the 2 workers generates its own key**. Sessions and CSRF tokens signed by worker A are rejected by worker B — login appears to randomly fail ~50% of requests. This fails *closed* (no security gap beyond UX/DoS-on-self), and no sensitive operation depends on session continuity across restarts: lockout state lives in `credentials.json`, not the session, and an invalidated session simply forces re-login. Conclusion for the scoped question: **UX/availability issue, not a security gap** — but the per-worker split makes it a hard-to-diagnose one.
3. `SESSION_COOKIE_SECURE` is never set ([rss_server.py:123-125](src/rss_server.py:123)). Deployed behind TLS (Cloudflare Tunnel), the session cookie will still be sent over a plain-HTTP hop if one exists. Add a `BIND_COOKIE_SECURE` config (default false for LAN-HTTP homelab use, documented for tunnel users).

**Resolution.** Move secret-key resolution after the config load; log a CRITICAL (not WARNING) when falling to ephemeral mode and consider refusing to start with auth enabled + ephemeral key; add the `Secure`-flag config.

**Migration flag:** YES if `BIND_COOKIE_SECURE` is added (new config key); NO for the ordering fix.

### **[LOW] SEC-7 — Account lockout: durable but globally DoS-able, and racy across workers**

**Diagnosis (durability — the scoped question).** Verified all paths: `change_password()` preserves `failed_attempts`/`locked_until` ([security.py:284-289](src/security.py:284)); `save_credentials()` resets them but is unreachable once setup is complete ([rss_server.py:393](src/rss_server.py:393)); the v1→v2 migration uses `setdefault` ([security.py:163-171](src/security.py:163)); `POST /api/settings` touches only `config.env`, never `credentials.json`; daemon restart doesn't touch it. **No unintended reset path exists.** Two real issues:
1. **Global lockout = remote DoS.** Five wrong passwords from *any* IP lock the only account for 15 minutes ([security.py:326-349](src/security.py:326)) — and since `verify_credentials` also counts wrong-*username* attempts ([security.py:383-385](src/security.py:383)), an unauthenticated attacker (who passes the IP allowlist — see SEC-3) can lock the operator out indefinitely with one request per ~3 minutes.
2. **Lost-update race.** `record_failed_login`/`record_successful_login` do read → modify → write with locks held only during the individual read and write, not across them ([security.py:326-349](src/security.py:326)). Two gunicorn workers handling concurrent failures can drop a count. Low impact (counter drift), but it weakens the lockout slightly.

**Resolution.** Track failures per source IP (dict in `credentials.json` or a small SQLite table) with the global lock as a fallback ceiling; hold `LOCK_EX` across the read-modify-write (open `r+`).

**Migration flag:** YES if per-IP tracking changes the `credentials.json` schema (v3 + migration); NO for the locking fix.

### **[LOW] SEC-8 — CSRF: coverage complete; minor hardening gaps**

**Diagnosis (scoped verification).** `csrf_protect` is a `before_request` hook ([rss_server.py:200-207](src/rss_server.py:200)) that fires for **every** POST: `/api/*` paths validate the `X-CSRF-Token` header, everything else the form field. There are no PUT/DELETE/PATCH routes. Confirmed covered: `/api/trigger-scrape`, `/api/scraping/enable`, `/api/settings`, `/api/settings/trackers`, `/api/settings/password`, `/api/login`, `/api/logout`, `/api/setup` — i.e. **full coverage of all state-mutating routes**, including login (login-CSRF protected). Token lifecycle: one `secrets.token_hex(32)` per session, never rotated, valid for the 24h session lifetime; replay within a session is by-design for the double-submit-into-session pattern and is acceptable. Hardening nits: (1) comparison uses `!=` instead of `hmac.compare_digest` ([rss_server.py:171](src/rss_server.py:171), [178](src/rss_server.py:178)); (2) the token is not rotated after login/logout, so a pre-login token survives privilege elevation; (3) `SameSite=Lax` is set, which already neutralizes classic cross-site POST in modern browsers — good defense in depth.

**Resolution.** Use `hmac.compare_digest`; rotate the token inside `api_login` on success (call `session.pop("csrf_token")` then re-issue — the SPA already refetches on 401/403 via `invalidateCsrf()`, but add a refetch after login to avoid one failed request).

**Migration flag:** NO.

### **[LOW] SEC-9 — No session regeneration on login (fixation hygiene)**

**Diagnosis.** `api_login` sets `session["authenticated"] = True` without clearing the pre-auth session ([rss_server.py:357-360](src/rss_server.py:357)). With Flask's client-side cookie sessions, exploitation requires the attacker to plant a cookie (subdomain/MITM), so risk is low — but `session.clear()` before marking authenticated (re-issuing the CSRF token) is one line.

**Migration flag:** NO.

### **[INFO] SEC-10 — Injection pipeline: clean end-to-end (verified)**

Traced attacker-controlled titles from scrape → store → RSS → React:
- **SQLite:** every statement is parameterized — `add_magnet` ([storage.py:128-132](src/core/storage.py:128)), `search` ([storage.py:167-191](src/core/storage.py:167)), `migrate.py` bulk insert ([migrate.py:72-77](src/core/migrate.py:72)). The FTS5 sync triggers reference `new.title`/`old.title` *inside the trigger DDL* ([storage.py:32-41](src/core/storage.py:32)) — values flow through SQLite's engine, never through string formatting. No injection surface.
- **FTS5 search input (assessed independently):** the query arrives as a bound `LIKE ?` parameter against the trigram table ([storage.py:184](src/core/storage.py:184)) — BIND deliberately avoids the `MATCH` operator, which would have been a query-syntax injection/DoS surface. Verdict: safe. Functional nit: user-supplied `%`/`_` wildcards are not escaped, so a search for `100%` behaves unexpectedly — cosmetic.
- **RSS XML:** titles are emitted in CDATA with the `]]>` splitting countermeasure ([rss_server.py:298](src/rss_server.py:298)); the magnet link is `escape()`d ([rss_server.py:297](src/rss_server.py:297)); the GUID is a validated hex hash. No XML injection.
- **React:** no `dangerouslySetInnerHTML`/`innerHTML` anywhere in `frontend/src` (grep-verified); `DataTable` renders cells via `String()` as text nodes ([DataTable.tsx:190-195](frontend/src/fujin/components/DataTable.tsx:190)).

### **[INFO] SEC-11 — Secrets at rest: not in git; two local-disk anomalies on this machine**

`git ls-files` and history checks confirm no credentials, keys, DB, or logs are tracked. Two on-disk findings on the dev machine (likely WSL→macOS migration artifacts, related to the migration-audit memory):
1. `data/.secret_key` is mode **0666** (world-writable) despite the code chmod'ing 0600 at creation — permissions were lost in the migration. Fix: `chmod 600 data/.secret_key`, or regenerate.
2. A stale `credentials.json` (v2 schema, real scrypt hash, June 4) sits at the **repo root** — a leftover from a pre-`data/` layout. It is gitignored but feeds the SEC-4 Docker-context exposure. Delete it.
Also note the small TOCTOU in `_save_credentials_raw` ([security.py:181-187](src/security.py:181)): the file is written with default umask, then chmod'd — use `os.open(..., 0o600)` to close the window.

---

## Architecture

### **[HIGH] ARCH-1 — Daemon status heuristic: broken in the recommended deployment; replace with a DB heartbeat**

**Diagnosis.** `check_daemon_status()` ([rss_server.py:259-278](src/rss_server.py:259)) reads `logs/bind.log` mtime. Confirmed audit item 2, plus one worse fact: in the **dual-container compose file**, `bind-daemon` mounts `./logs:/app/logs` but **`bind-rss` has no logs mount at all** ([docker-compose.yml](docker-compose.yml) — only the `data` volume is shared). The RSS container's `/app/logs/bind.log` never exists, so status is permanently `"unknown", "Log file not found"` in the deployment the README recommends. The Dashboard and `/api/stats` ship a status that is wrong by construction. (Side effect: `/api/logs?log=daemon` is also empty in this mode, and `security.log` written by the RSS container is lost on container recreation.)

**Replacement — evaluation of the four candidates:**

| Candidate | Verdict |
|---|---|
| **Heartbeat row in SQLite (chosen)** | The `data` volume + WAL database is the *only* channel already shared by both processes in every deployment mode. Writes are transactional (no partial-read concern), readable from any worker, and enable a real Docker HEALTHCHECK. Cost: one tiny write per beat — negligible WAL churn at a 30s cadence. |
| PID file + `kill(pid, 0)` | **Rejected.** The two containers have separate PID namespaces; the daemon's PID is meaningless inside `bind-rss`, and signal-0 probes are impossible across containers. Only works bare-metal. |
| Status file with timestamp | Workable, but it adds yet another unsynchronized sentinel file with partial-write and clock-skew concerns — and the transactional shared DB already exists. Strictly dominated by the heartbeat row. |
| Unix socket | **Rejected.** Requires a listener thread in the daemon, socket lifecycle management on a named volume (stale socket files after crashes), and gives no more fidelity than a timestamp. Highest complexity for no gain. |

Recommend a dedicated single-row table over piggybacking `scrape_runs` (a job-granularity log — beats at 30s would pollute it and break the metrics page):

```sql
CREATE TABLE IF NOT EXISTS daemon_heartbeat (
    id           INTEGER PRIMARY KEY CHECK (id = 1),
    beat_at      TEXT    NOT NULL,          -- UTC ISO-8601
    state        TEXT    NOT NULL,          -- 'idle' | 'scraping' | 'disabled'
    interval_min INTEGER NOT NULL
);
```

Daemon: `INSERT OR REPLACE` from the main loop, throttled to every 30s (and immediately on state change). RSS server: `online` if `beat_at` is within 90s, with `state='disabled'` rendered distinctly; fall back to the mtime heuristic when the row is absent (rolling-upgrade compatibility — see roadmap sequencing). This also fixes the false-positive in audit item 2 (any process touching the log reads as "online").

**Migration flag:** YES — DB schema addition (additive; `_init_schema` `CREATE TABLE IF NOT EXISTS` is sufficient, no data migration). Coordinated daemon + RSS change.

### **[MEDIUM] ARCH-2 — `SCRAPING_ENABLED` state machine: a stale sentinel can silently re-enable scraping against config**

**Diagnosis.** The full state machine, with `C` = config value and `D` = daemon runtime flag ([bind.py:222-240](src/bind.py:222)):

- **Boot:** `D ← env(SCRAPING_ENABLED)`, where env was seeded from config — so `D = C` at startup.
- **Enable** (`POST /api/scraping/enable`, [rss_server.py:557-577](src/rss_server.py:557)): writes `C=true`, touches `.enable-scraping`, attempts systemd restart. A daemon running with `D=false` consumes the sentinel and enables — correct, no restart needed.
- **Disable** (`POST /api/settings` with `SCRAPING_ENABLED=false`): writes `C=false` and calls `restart_daemon()`. **There is no disable sentinel.** On systemd this works via restart; **in Docker the restart is a no-op**, so the daemon keeps scraping with `D=true` while `C=false`.

**The out-of-sync sequence (Docker):**
1. User disables scraping → `C=false`, restart fails silently → `D=true`. **User-visible result:** the Dashboard shows the "Archiving is paused / Begin Archiving" banner ([DashboardPage.tsx:132-181](frontend/src/pages/DashboardPage.tsx:132), driven by `C` via `/api/stats`) while the Metrics page keeps accumulating new scrape runs. The UI claims paused; the daemon scrapes.
2. Worse — **stale-sentinel re-enable:** the daemon only consumes `.enable-scraping` when `D=false` ([bind.py:232](src/bind.py:232)). If the enable endpoint ever fires while `D=true` (exactly the mismatch state from step 1, where `C=false` lets the route proceed), the sentinel is written and never consumed. The next time the daemon legitimately starts disabled (`C=false` after a real restart), it finds the stale sentinel and **immediately re-enables scraping in direct contradiction of the config**.

**Resolution (preserves the no-restart enable path).** Collapse to a single source of truth: have the daemon re-read `SCRAPING_ENABLED` from `config.env` once per main-loop tick (a 1 Hz flock'd read of a <1 KB file is negligible; or check the file's mtime first). This gives no-restart *enable and disable*, removes the sentinel entirely, and makes `C` authoritative. Transition safety: the daemon deletes any leftover `.enable-scraping` at startup. Keep `.trigger` as-is (different concern — see ARCH-3).

**Migration flag:** NO (config format unchanged; sentinel removed). Coordinated daemon + RSS change (the enable endpoint stops touching the sentinel).

### **[MEDIUM] ARCH-3 — Sentinel-file IPC: stale `.trigger` deadlocks manual scrapes and double-fires on restart**

**Diagnosis (scoped question: daemon exits while `.trigger` exists).** `POST /api/trigger-scrape` returns **409 "A trigger is already pending"** whenever the file exists ([rss_server.py:655-656](src/rss_server.py:655)). If the daemon dies (or was never started) after a trigger is written, the file persists indefinitely: every subsequent manual trigger 409s until the daemon comes back. On daemon restart there is **no cleanup path** — startup unconditionally runs a job (when enabled, [bind.py:225](src/bind.py:225)), then the first loop iteration finds the leftover `.trigger` and runs a **second, immediate job** ([bind.py:241-247](src/bind.py:241)) — a double scrape against ABB right after every restart-with-pending-trigger, which is exactly the hammering pattern the circuit breaker exists to avoid. Also note audit item 8 confirmed: triggers accumulate meaninglessly when no daemon runs, while the UI reports "Scrape job triggered — results in ~60s."

**Resolution.** (a) Daemon deletes both sentinels at startup *before* the initial scheduled run. (b) The trigger route treats a `.trigger` older than ~2× `SCRAPE_INTERVAL` as stale: overwrite instead of 409. (c) Longer term, fold triggers into the heartbeat table (`requested_run_at` column) — the RSS server can then also tell the user honestly that no daemon has picked the trigger up. The file mechanism is otherwise acceptable for this deployment model (same-volume, single consumer).

**Migration flag:** NO (or folded into ARCH-1's schema if option (c) is taken).

### **[MEDIUM] ARCH-4 — Config write is a non-atomic truncate-in-place, and the UI save clobbers `BIND_DB_PATH`**

**Diagnosis (scoped race question).** `write_config` opens with `"w"` — **truncating the file — before acquiring `LOCK_EX`** ([config_manager.py:160-165](src/config_manager.py:160)). A daemon starting (or the RSS server importing) between truncate and write reads an empty file under its `LOCK_SH` and silently gets **all defaults** ([config_manager.py:77-80](src/config_manager.py:77)): `SCRAPE_INTERVAL=60`, `SCRAPING_ENABLED=true`, etc. The systemd restart sequence widens exposure: `systemctl restart` SIGTERMs the old daemon (which drains up to its job timeout — see RES-4) and the new daemon's config read can land anywhere in that window. Additionally `restart_daemon()`'s 30s subprocess timeout ([config_manager.py:249-254](src/config_manager.py:249)) is shorter than a drain, so a restart during an active job reports "Daemon restart timed out" to the user even though the restart proceeds.

**Separate clobber bug found while tracing this path:** `api_settings_post` builds `new_config` **without `BIND_DB_PATH`** ([rss_server.py:533-545](src/rss_server.py:533)), and `write_config` emits every `DEFAULTS` key using `settings.get(key, DEFAULTS[key])` ([config_manager.py:147-149](src/config_manager.py:147)) — so every UI save rewrites `BIND_DB_PATH=data/bind.db`, silently discarding a custom DB path stored in `config.env`. Docker masks it (env wins) and the systemd units happen to resolve the relative default to the same file, but any non-standard install loses its DB pointer on the next settings save and the restarted daemon starts an **empty database**.

**Resolution.** Use the tmp-file + `fsync` + `os.replace` pattern that already exists in `TrackerManager.save()` ([tracker_manager.py:64-81](src/core/tracker_manager.py:64)) — `os.replace` is atomic, so readers see old-or-new, never empty (flock on the tmp file can be dropped; readers lock the target). For the clobber: carry `BIND_DB_PATH` through from `read_config()` in `api_settings_post`, or better, make `write_config` start from the current file contents and overlay only submitted keys.

**Migration flag:** NO.

### **[MEDIUM] ARCH-5 — `check_same_thread=False` masks one real concurrent-access window in the daemon**

**Diagnosis (scoped question).** Per-process analysis:
- **gunicorn workers:** each sync worker is a separate *process* that imports the module and constructs its own `MagnetStore` — no cross-thread sharing; WAL gives each reader snapshot isolation against the daemon's writes, and `busy_timeout=5000` covers write contention. The audit's claim holds here.
- **daemon:** it does **not** hold. `run_job_with_timeout` runs on the main thread and blocks in `future.result(timeout=JOB_TIMEOUT)` ([bind.py:195](src/bind.py:195)). On **timeout**, the main thread proceeds to `store.record_scrape_run(...)` in the `finally` ([bind.py:209](src/bind.py:209)) **while the executor thread is still inside `run_job` using the same `sqlite3.Connection`** for `has_hash`/`add_magnet`. Two threads, one connection, `isolation_level=None` — this is exactly what `check_same_thread=False` is silencing. CPython's sqlite3 in serialized threading mode prevents corruption, but statement interleaving on an autocommit connection is undefined behavior territory across Python/SQLite builds.

**Resolution.** Smallest correct fix: record the timeout run on a short-lived second connection (`sqlite3.connect(db_path)` inside `record_scrape_run`, or give `MagnetStore` a `threading.local` connection pool keyed by thread). Alternative: have the *job thread* record its own run results and let the main thread only record the timeout marker after `future.result()` eventually returns. Do not rely on serialized mode.

**Migration flag:** NO.

### **[LOW] ARCH-6 — Docker hardcodes scrape interval; single-container uses a different env var name**

`docker-compose.yml` passes `--interval 60` on the command line, which (Click precedence: explicit flag > envvar) **silently overrides** `SCRAPE_INTERVAL` from config or env — the Settings field does nothing in dual-container Docker. `docker/entrypoint.sh` reads `${BIND_SCRAPE_INTERVAL:-60}` — a variable name that exists nowhere else in the codebase (config key is `SCRAPE_INTERVAL`). Fix: drop `--interval` from the compose command and unify on `SCRAPE_INTERVAL`. **Migration flag:** NO (compose/entrypoint only). Note this interacts with ARCH-2: today, interval changes in Docker require recreating the container *and* are then ignored anyway.

---

## Resilience

### **[MEDIUM] RES-1 — Proxy eviction is permanent for the daemon's lifetime, and unrelated failures evict proxies**

**Diagnosis (scoped question).** `ProxyPool._failed` is only ever added to ([egress_manager.py:42-45](src/core/egress_manager.py:42)); the `EgressManager` lives as long as the `BindScraper`, which lives as long as the daemon process ([bind.py:160](src/bind.py:160)) — typically months. So eviction is **permanent until daemon restart**. Operational impact: during a transient ABB outage (site down, not proxy down), each job's `fetch()` exhausts all layers and calls `mark_failed(proxy)` — evicting one healthy proxy per failing URL. A few hours of site flap can drain the entire pool; when ABB recovers, the daemon runs direct-or-cloudscraper only, permanently degraded. Compounding bug: `mark_failed` fires when the **cloudscraper** layer fails too ([egress_manager.py:108-109](src/core/egress_manager.py:108)) — even when the failure had nothing to do with the proxy, and it double-marks the same proxy after the proxy layer already failed.

**Resolution.** Replace the `set` with `dict[str, float]` of eviction timestamps and re-admit proxies after a cooldown (e.g., 30 min) in `get_next()`; only mark a proxy failed from the `curl_cffi_proxy` layer, and only when the direct layer *succeeded recently or failed differently* is too clever — the cooldown alone removes the permanence and is enough.

**Migration flag:** NO.

### **[MEDIUM] RES-2 — Transient-network retry classification never matches real exceptions**

**Diagnosis.** `RetryEngine.execute` retries on `isinstance(e, (ConnectionError, TimeoutError))` — the Python **builtins** ([retry.py:71](src/core/retry.py:71)). Neither egress library raises them: `curl_cffi` raises its own `RequestsError`/`CurlError` hierarchy; `cloudscraper` (requests-based) raises `requests.exceptions.ConnectionError`/`Timeout`, which subclass `RequestException(IOError)` — *not* the builtin `ConnectionError`. So every real connection failure or timeout falls into the final `else` ("Non-retryable error … escalating", [retry.py:81-86](src/core/retry.py:81)) and **escalates immediately with zero in-layer retries**. The waterfall still tries the next layer, so total failure isn't guaranteed — but the documented "3 retries with backoff per layer" behavior only exists for HTTP-status errors. The unit tests raise builtin `ConnectionError` and pass, masking this.

**Resolution.** Classify by library exception types (import both; `requests.exceptions.ConnectionError/Timeout`, `curl_cffi.requests.exceptions.RequestException` subtypes / `CurlError` with timeout-ish `curl_code`s), or duck-type more broadly (`isinstance(e, OSError)` catches the requests family; add curl_cffi explicitly). Add a regression test that raises the *actual* library exceptions.

**Migration flag:** NO.

### **[INFO] RES-3 — Request budget × schema drift: no amplification (verified), but drift never throttles anything**

**Diagnosis (scoped question).** Schema drift and egress retries **cannot compound**: `SchemaHealthMonitor.record()` is only reached *after a successful fetch* ([scraper.py:126-133](src/core/scraper.py:126)) — a parse failure logs `CRITICAL SCHEMA_DRIFT_DETECTED` and moves on; `extract_info_hash` never refetches. Worst-case egress per job: 1 RSS fetch (≤9 requests) + per-book detail fetches (≤9 each) with 2–5s jitter between pages, and the circuit breaker opens after 3 consecutive `FetchExhausted` ([scraper.py:99-102](src/core/scraper.py:99)) — bounding a fully-blocked job at ~36 outbound requests. Once open, remaining books short-circuit in `_get_page`. **No retry storm exists.** Two design notes: (a) cooldown (default 300s) ≪ interval (60 min), so the breaker is always reset by the next job — it protects within a job, not across jobs, which is acceptable; (b) a CRITICAL drift alert changes *no behavior* — the daemon happily refetches 20 unparseable pages every hour forever. Consider: when drift is active, skip detail fetches for the remainder of the job (the RSS fetch alone is enough to detect recovery).

**Migration flag:** NO.

### **[INFO] RES-4a — Circuit-breaker reset race: verified safe**

**Diagnosis (scoped verification).** The skip-if-running guard runs **first**, on the main thread, before any submission: `run_job_with_timeout` checks `prev.done()` at [bind.py:179-185](src/bind.py:179) and returns before `executor.submit`. `can_attempt()` is called only inside the job thread ([scraper.py:87](src/core/scraper.py:87)), and `max_workers=1` plus the done-check guarantees a single job thread exists; the breaker is never read or reset concurrently. The time-based reset in `can_attempt` ([scraper.py:58-68](src/core/scraper.py:58)) is therefore single-threaded. **Ordering is correct as implemented.** (Fragility note: this invariant lives entirely in the done-check; a comment pinning it would be cheap insurance.)

### **[MEDIUM] RES-4 — SIGTERM drain: bounded in the normal case, unbounded after a timeout; both supervisors SIGKILL mid-job**

**Diagnosis (scoped question).** The handler sets a flag ([bind.py:165-168](src/bind.py:165)); the main thread is usually blocked in `future.result(timeout=JOB_TIMEOUT)`, so the drain **does respect the timeout** — shutdown happens at job-end or timeout, whichever is first. The gap is *after* a timeout: the abandoned job thread keeps running, and on `sys.exit(0)` Python's atexit joins the non-daemon `ThreadPoolExecutor` thread **unconditionally** — a hung network call (and RES-2 shows real timeouts aren't classified, so a stuck socket is plausible) blocks exit forever. There is **no hard-shutdown path**. Supervisor reality: `deployment/bind.service` sets no `TimeoutStopSec` → systemd default 90s → **SIGKILL mid-job** whenever a drain exceeds 90s (any non-trivial job); `docker stop` grace default is **10s** (no `stop_grace_period` in compose) → effectively every active-job shutdown in Docker is a SIGKILL. SQLite/WAL makes this crash-safe data-wise, but in-flight work is lost and "graceful drain" is mostly fiction under both supervisors.

**Resolution.** (1) Call `_job_executor.shutdown(wait=False, cancel_futures=True)` on the shutdown path and use `os._exit(0)` after the loop if the future is in timeout-abandoned state — or create the executor's thread as a daemon thread (`thread_name_prefix` + custom factory). (2) Set `TimeoutStopSec=` ≥ a sane drain budget (e.g., 120s) **and** shrink the per-shutdown drain: on SIGTERM, wait at most e.g. 60s for the current job rather than the full remaining `BIND_JOB_TIMEOUT`. (3) Add `stop_grace_period: 75s` to `bind-daemon` in compose.

**Migration flag:** NO (service-file + compose change; flag in release notes).

### **[LOW] RES-5 — Disk-space guard: placement is adequate; the actual disk risk is the unbounded `bind.log`**

**Diagnosis (scoped question).** The 100 MB check at job start ([bind.py:54-56](src/bind.py:54)) is proportionate: a job writes at most a few hundred ~200-byte rows plus bounded WAL growth (auto-checkpoint at 1000 pages), so per-write gating would add complexity for a failure mode SQLite already handles loudly (`SQLITE_FULL` → caught per-book at [bind.py:96-98](src/bind.py:96)). Keep as-is. The genuine unbounded writer is **`logs/bind.log`**: a plain `FileHandler` ([bind.py:21-28](src/bind.py:21)) with per-page debug/info lines, never rotated (only `security.log` rotates). Months of hourly jobs will eat the disk the guard is watching. Secondary: `/api/logs` does `f.readlines()` on that file ([rss_server.py:628-630](src/rss_server.py:628)) — loading a multi-GB log into the gunicorn worker. Fix both with `RotatingFileHandler(maxBytes=10MB, backupCount=3)` and a tail-read (seek from end) in `/api/logs`.

**Migration flag:** NO.

---

## Code Quality and Type Safety

### **[MEDIUM] CQ-1 — mypy "strict" is softened exactly where runtime type risk lives**

**Diagnosis (scoped question).** Zero inline `# type: ignore` in `src/` (verified) — good. But [pyproject.toml](pyproject.toml) carves out: (1) `ignore_missing_imports` for `cloudscraper`, `bs4`, `schedule`, `flask`(*), `curl_cffi.*`, `click`, `werkzeug.*` — every I/O boundary is untyped; (2) `disable_error_code = ["untyped-decorator", "no-any-return"]` for `src.rss_server`, `src.bind`, `src.security` — the three largest modules. The `Any` census (28 occurrences) concentrates precisely on the surfaces the scope flags: the egress layer (`_cffi_session: Any`, `cast(Any, response)` in [egress_manager.py:63,115](src/core/egress_manager.py:63)), the retry engine's fully-`Any` duck-typed `execute` ([retry.py:30-41](src/core/retry.py:30)) — which is how RES-2's misclassification survived type checking — and credential reads (`load_credentials() -> dict[str, Any]`, every field access unchecked, [security.py:137-156](src/security.py:137)). Verdict: **the configuration is strict in name; the call sites most likely to carry runtime type errors are exempted.**

**Resolution.** Define a small `Protocol` for HTTP responses (`status_code`, `text`, `headers.get`) and type the retry engine against it; flask/werkzeug ship type stubs — drop those two from `ignore_missing_imports`; replace the credentials dict with a `dataclass` + validating loader (also fixes the SEC-7 schema-drift class of bug); remove the per-module `disable_error_code` and fix the ~dozen fallout errors.

**Migration flag:** NO.

### **[INFO] CQ-2 — Error propagation out of `EgressManager.fetch()`: verified contained**

**Diagnosis (scoped question).** `fetch()` can raise exactly one exception type in practice: `FetchExhausted` ([egress_manager.py:111](src/core/egress_manager.py:111)) — `RetryEngine.execute` swallows everything else and returns `None`. The single caller, `BindScraper._get_page`, catches `FetchExhausted` explicitly ([scraper.py:99-102](src/core/scraper.py:99)) and returns `None`; `get_recent_books`/`extract_info_hash` are `None`-safe. If anything *else* ever escaped (e.g., a future bug in `ProxyPool`), the chain still holds: `run_job` wraps per-book saves ([bind.py:96-98](src/bind.py:96)), and `run_job_with_timeout` catches all exceptions from `future.result()`, logs, and **records a `failure` run in the `finally`** ([bind.py:206-209](src/bind.py:206)) — the scheduler never sees an exception and the loop continues. Confirmed: a `FetchExhausted` escaping `get_recent_books` would be caught by `run_job_with_timeout`, recorded as `failure`, and the daemon survives. One encapsulation nit: `probe_target` reaches into `self.egress._cffi_session` ([scraper.py:202](src/core/scraper.py:202)) — add a public `probe()` on `EgressManager`.

### **[MEDIUM] CQ-3 — Proxy credentials leak into logs (and into the UI log viewer)**

**Diagnosis (scoped scan).** Proxy URLs routinely embed credentials (`socks5://user:pass@host` — the Settings UI placeholder even suggests this format, [SettingsPage.tsx:148](frontend/src/pages/SettingsPage.tsx:148)). They are logged verbatim: `mark_failed` logs the full proxy URL at WARNING ([egress_manager.py:45](src/core/egress_manager.py:45)) into `bind.log`, which `/api/logs` then renders in the browser; `bind.py:139` logs raw env-vs-file values at DEBUG for mismatched keys, including `BIND_PROXY`/`BIND_PROXIES`. Clean elsewhere: no request/response bodies are logged (only URLs of public ABB pages), credential-file contents never appear in error paths, and magnet URIs at DEBUG are public data.

**Resolution.** Add a `redact_proxy(url)` helper (strip `user:pass@`) and use it in both sites; drop the config-mismatch debug line or log key names only.

**Migration flag:** NO.

### **[LOW] CQ-4 — Dead code and flat-file-era residue**

Inventory (all verified unreferenced from live code):
- **`src/templates/*.html` + `src/static/css/`** — the entire Vesper-era server-rendered UI. No `render_template` call exists in `src/`; Flask's `template_folder` ([rss_server.py:85](src/rss_server.py:85)) and the `app.jinja_env.globals["csrf_token"]` registration ([rss_server.py:182](src/rss_server.py:182)) serve nothing. Delete templates, the CSS dir, and the jinja global.
- **`requires_auth` + `check_auth`** ([security.py:504-563](src/security.py:504)) — Basic-Auth path; not imported by `rss_server.py` or anything else. Delete (the CLAUDE.md note about `@requires_auth` in tests refers to the session decorator's bypass env var; the tests that cover these functions directly can go with them).
- **`_validate_csrf_form`** ([rss_server.py:168-172](src/rss_server.py:168)) — only reachable for POSTs to non-`/api/` paths, of which none exist (the SPA catch-all is GET-only). Keep the hook but it's vestigial; if templates are deleted, simplify `csrf_protect` to header-only.
- **`/api/dashboard` route + `dashboard.get` client** — see SEC-1.
- **`TrackerManager.get_default_trackers`** ([tracker_manager.py:100-102](src/core/tracker_manager.py:100)) — unused.
- **`ConfigManager.read_config` uses `print()`** instead of its logger ([config_manager.py:101](src/config_manager.py:101)) — invisible under gunicorn/systemd journal filtering.
- **Flat-file residue:** `data/magnets/` still holds `history.log`, `magnets_2026-01-26.txt` (expected — `migrate.py` input, audit item 9); stale root `credentials.json` (SEC-11); `src/bind.egg-info/` on disk (gitignored, harmless).
- **Version skew (audit item 1):** `pyproject.toml` 2.2.0 vs `CHANGELOG.md` 1.2.1. Pick one: either backfill changelog entries for 2.x or reset pyproject to 1.2.1 before the next tag — `docker-publish.yml` derives image tags from git tags, so the skew will eventually mint a misleading image version.

**Migration flag:** NO.

---

## Test Suite

### **[HIGH] TEST-1 — Auth guards have near-zero effective coverage (confirmed)**

**Diagnosis (scoped question).** [tests/conftest.py](tests/conftest.py) sets `BIND_AUTH_ENABLED=false` process-wide, so every `@requires_session_auth` route is exercised with the guard short-circuited. Dedicated auth-enabled tests exist for exactly **one protected route**: `/api/trigger-scrape` (401 unauthenticated + 200 authenticated, [test_rss_server.py:544-624](tests/test_rss_server.py:544)) plus `/api/me` semantics. Never tested with auth enforced: `/api/stats`, `/api/metrics`, `/api/settings` GET+POST, `/api/scraping/enable`, `/api/settings/trackers`, `/api/settings/password`, `/api/logs`. **A missing decorator on any of those routes would ship through CI green at 97.5% coverage.** Given SEC-1 shows a decorator *was* in fact missing/omitted on a data route, this is not hypothetical.

**Resolution.** One parametrized matrix test: for every route in a literal list of protected endpoints, with `BIND_AUTH_ENABLED=true` and no session, assert 401; with an authenticated session, assert non-401. Add a meta-assertion that the list covers every registered `/api/` rule except an explicit public allowlist (`/api/login`, `/api/logout`, `/api/me`, `/api/csrf-token`, `/api/setup*`, plus whatever SEC-1's resolution keeps public) — that makes *forgetting to update the test* fail loudly too.

**Migration flag:** NO.

### **[MEDIUM] TEST-2 — CSRF tests: negative paths present; depth verified, two gaps**

**Diagnosis (scoped question).** Confirmed real negative testing, not just success path: missing token → 403 ([test_rss_server.py:436](tests/test_rss_server.py:436)), wrong token → 403 ([test_rss_server.py:440](tests/test_rss_server.py:440)), token stability across requests ([test_rss_server.py:425](tests/test_rss_server.py:425)). "Replayed token" is not a meaningful negative for the session-bound pattern (reuse within a session is by design) — correctly absent. Gaps: no test that a *form-field* token is rejected on an `/api/` route (header-vs-form channel confusion), and no test that a token from session A fails against session B (the actual binding property). Both are two-liners.

**Migration flag:** NO.

### **[MEDIUM] TEST-3 — Integration layer is empty; the daemon main loop is coverage-exempt by annotation**

**Diagnosis (scoped question).** `tests/integration/` contains only `__pycache__` — **zero integration tests exist.** All three scoped candidates are absent: sentinel-file IPC daemon↔RSS (worse: the entire main loop including sentinel consumption is annotated `# pragma: no cover`, [bind.py:230-248](src/bind.py:230) — the 97.5% figure structurally excludes it), the `write_config → restart_daemon` sequence (unit-tested only with subprocess mocked), and the WAL-probe failure path on a network filesystem (unit-tested via monkeypatch in `test_storage_probe.py`, never against a real non-WAL-capable mount — acceptable to leave as unit-level, but say so in docs). The ARCH-2/ARCH-3 bugs live precisely in the uncovered loop.

**Resolution.** Extract the loop body (`process_sentinels(state) -> state`) into a testable function — the `pragma: no cover` lines then shrink to the `while`/`sleep` shell — and add an integration test that runs the real daemon function against a tmpdir with sentinel files. A compose-based smoke test (both containers, assert `/api/stats` reports online via the ARCH-1 heartbeat) belongs in CI post-ARCH-1.

**Migration flag:** NO.

### **[LOW] TEST-4 — Circuit breaker edges covered; FTS trigger sync is not**

**Diagnosis (scoped questions).** Circuit breaker: time-reset path covered (`test_cooldown_allows_retry`, `test_cooldown_resets_on_retry`, [test_circuit_breaker.py:53,76](tests/test_circuit_breaker.py:53)); skip-if-running covered (`test_skips_run_when_previous_job_still_running`, [test_bind_daemon.py:360](tests/test_bind_daemon.py:360)); timeout recording covered ([test_bind_daemon.py:383](tests/test_bind_daemon.py:383)). True *concurrent submission* isn't simulated, but the single-threaded scheduler makes the done-check test the right level. FTS: the <3-char LIKE fallback is covered twice ([test_storage.py:119](tests/test_storage.py:119), [test_storage_extended.py:209](tests/test_storage_extended.py:209)) and the boundary (len-3 query) is implicitly exercised; **no test touches the UPDATE or DELETE sync triggers** (`magnets_au`/`magnets_ad`, [storage.py:35-41](src/core/storage.py:35)) — nothing in the app deletes/updates magnets today, but `migrate.py`'s rebuild assumes trigger correctness and future pruning features will too. Add one test: insert → update title → assert FTS finds new not old → delete → assert FTS empty.

**Migration flag:** NO.

---

## Dependencies

Checked live against PyPI (2026-06-12) and `npm audit`.

### **[MEDIUM] DEP-D1 — cloudscraper 1.2.71: latest release, abandoned project**

1.2.71 **is** the newest version on PyPI — and it shipped in mid-2023. Three years without a release for a library whose entire job is tracking an adversarial, fast-moving target (Cloudflare's challenge logic). Its challenge-solving is stale enough that its value as the last waterfall layer is questionable; it also drags an unpinned `requests` stack into the image. Options, in order: (a) drop the layer and lean on curl_cffi with current impersonation targets (DEP-D2) — measure layer-3 success rate from logs first; (b) replace with a maintained equivalent if the success-rate data says layer 3 still earns its keep. **Migration flag:** NO (internal).

### **[LOW] DEP-D2 — curl_cffi 0.15.0 is current; `impersonate="chrome120"` is ~2.5 years stale**

The pin is the latest release (verified). But the hardcoded `chrome120` ([egress_manager.py:63](src/core/egress_manager.py:63)) imitates a browser from late 2023 — a TLS/JA3+HTTP2 fingerprint that no longer matches any live Chrome population, which is itself a detectable anomaly to Cloudflare. curl_cffi 0.15 ships newer targets (chrome131+ and rolling aliases). **Resolution:** bump to the newest supported `chromeNNN`, and make it configurable (`BIND_IMPERSONATE`, default = newest) so future rotations don't need a release. **Migration flag:** YES if the config key is added; NO for the literal bump.

### **[LOW] DEP-D3 — Remaining pins: Python minor lag only; npm tree clean**

- Current: flask 3.1.3 ✓, gunicorn 26.0.0 ✓, click 8.1.7, schedule 1.2.2.
- Behind: beautifulsoup4 4.12.3 → 4.15.0 (three minors; 4.13 changed some typing/encoding behavior — bump deliberately with the scraper tests), lxml 6.1.0 → 6.1.1 (patch).
- `pip-audit` runs in CI on both requirements files ([ci.yml](. github/workflows/ci.yml) lint job) ✓ — no findings surfaced locally either.
- **Frontend:** `npm audit` (full transitive tree, with lockfile): **0 vulnerabilities** at any severity (verified). Top-level pins (React 18.3, Mantine 7, vite 7.3.5, react-router 6.26) are maintained lines; React 19 / router 7 migrations are discretionary, not hygiene.

**Migration flag:** NO.

---

## Frontend

### **[INFO] FE-1 — XSS via torrent titles: not exploitable (verified)**

Every component that renders title data was inspected: `DashboardPage`/`MagnetsPage` render titles through `DataTable`'s default cell path — `String(row[col.key])` as a React text node ([DataTable.tsx:190-195](frontend/src/fujin/components/DataTable.tsx:190)); `MetricsPage` renders only numeric/enum fields; no fujin component accepts HTML. Grep across `frontend/src` confirms **zero** `dangerouslySetInnerHTML`, `innerHTML`, `document.write`, or `eval`. React's default escaping is never bypassed.

### **[LOW] FE-2 — Magnet `href` handling: safe by server-side construction; add one client-side guard**

Magnet URIs are rendered as `<a href={row.magnet}>` in both Dashboard ([DashboardPage.tsx:260-271](frontend/src/pages/DashboardPage.tsx:260)) and Magnets ([MagnetsPage.tsx:116-123](frontend/src/pages/MagnetsPage.tsx:116)) pages. The scheme cannot be attacker-controlled: the string is built server-side as `f"magnet:?xt=urn:btih:{info_hash}&dn={quote_plus(title)}"` ([magnet.py:13](src/core/magnet.py:13)) — the hash is validated 40-hex/Base32-converted ([scraper.py:213-235](src/core/scraper.py:213)), and `quote_plus` percent-encodes every character that could break out of the `dn=` value, so a `javascript:`/`data:` prefix can never reach the scheme position. Residual risk is only a future refactor constructing hrefs client-side from raw fields. Cheap hardening: a `MagnetLink` component (or guard in `rowActions`) that renders a dead link unless `magnet.startsWith('magnet:?xt=urn:btih:')`. **Migration flag:** NO.

### **[INFO] FE-3 — CSRF token race: does not exist (verified)**

The token is fetched **lazily and awaited inline**: `apiFetch` awaits `getCsrfToken()` before dispatching any non-GET request ([client.ts:24-27](frontend/src/api/client.ts:24)) — the first mutating call cannot fire without a token, regardless of `AuthContext` bootstrap timing (which only calls `/api/me`, [AuthContext.tsx:32-41](frontend/src/context/AuthContext.tsx:32)). Concurrent first-POSTs both fetch the token, and the server returns the same session-stored value for both (`generate_csrf_token` is idempotent, [rss_server.py:162-165](src/rss_server.py:162)). 401/403 responses invalidate the cache for refetch ([client.ts:31-38](frontend/src/api/client.ts:31)). No race.

### **[LOW] FE-4 — Server exception strings flow to the UI**

The client wrapper itself is careful — it surfaces only `body.error ?? body.message` and never dumps response bodies ([client.ts:39-46](frontend/src/api/client.ts:39)) — but the **server** puts raw exception text into those fields: `f"Failed to update trackers: {e}"` ([rss_server.py:589](src/rss_server.py:589)), `f"Could not write trigger file: {e}"` ([rss_server.py:661](src/rss_server.py:661)), `f"Error reading log file: {e}"` ([rss_server.py:632](src/rss_server.py:632)), and `check_daemon_status`'s `f"Error checking status: {str(e)}"` ([rss_server.py:278](src/rss_server.py:278)) which renders on the unauthenticated-reachable dashboard status line. `OSError` text includes absolute filesystem paths. No stack traces leak (Flask debug off), and the audience is mostly authenticated — Low. **Resolution:** log the exception server-side, return generic messages. **Migration flag:** NO.

---

## Deployment

### **[HIGH] DEP-1 — Missing `.dockerignore`** — see SEC-4 (single finding, counted once).

### **[MEDIUM] DEP-2 — No HEALTHCHECK anywhere; `/health` neither reports daemon liveness nor is cheap**

No `HEALTHCHECK` exists in either Dockerfile, the compose file, or the unRAID template (grep-verified). Two design notes on `/health` as a candidate target ([rss_server.py:328-339](src/rss_server.py:328)): (1) it does **not** use the log-mtime daemon heuristic at all — contrary to the scope's premise, it reports only server-up + DB stats + an ABB probe; daemon liveness appears nowhere in it, so today's `/health` can't misroute traffic based on daemon state, but it also can't catch a dead daemon. (2) It instantiates a fresh `BindScraper` (new curl_cffi + cloudscraper sessions) every 5 minutes and makes an **outbound request to ABB** on cache miss — a health endpoint that depends on a third party's reachability and can take 10s is a bad orchestration probe. **Resolution:** make `/health` DB-only (move the probe to `/api/stats` or a `/health?probe=1` opt-in); add `HEALTHCHECK CMD curl -f http://localhost:5050/health` to the RSS container; after ARCH-1, give `bind-daemon` a healthcheck that reads the heartbeat row via a tiny `python -m src.healthcheck`. The mtime heuristic is unsuitable as any container's health signal — but the correct fix is ARCH-1's heartbeat, not patching the heuristic. **Migration flag:** NO.

### **[MEDIUM] DEP-3 — Non-root user ✓, but root-owned `/app` makes volumeless and bind-mount runs fail**

Both images correctly create and switch to uid 1001 (`useradd -r -u 1001 … USER bind`) — the containers do **not** run as root ✓. But `COPY . .` runs as root and no `mkdir`/`chown` follows, so `/app` is root-owned, mode 755. Consequences: a `docker run starlightdaemon/bind` without a volume dies at startup (`os.makedirs("/app/data")` → `PermissionError` → FATAL, [bind.py:147-149](src/bind.py:147)); host bind-mounts (`./logs:/app/logs` in compose; unRAID appdata) must be pre-chowned to uid 1001 or the daemon crashes in `logging.FileHandler` at import ([bind.py:21-28](src/bind.py:21)). **Resolution:** `RUN mkdir -p /app/data /app/logs && chown -R bind:bind /app/data /app/logs` before `USER bind`, declare `VOLUME /app/data`, and document the uid-1001 requirement for bind mounts (unRAID template description). **Migration flag:** NO.

### **[INFO] DEP-4 — Secrets injection and shared-volume write boundary: verified clean**

(Scoped verifications.) `FLASK_SECRET_KEY` appears only as a commented-out example in [docker-compose.yml](docker-compose.yml) and an empty-default variable in `unraid/bind.xml` — no committed defaults, nothing baked into images (modulo SEC-4's *local-build* context leak). Volume permissions: both containers run as uid 1001 sharing the `data` volume; the RSS server can write `config.env`/`trackers.json`/DB there **by design**, but nothing the daemon *executes or imports* lives on the volume — `entrypoint.sh` and all Python modules are in root-owned image layers the runtime user cannot modify. No write-to-execute path exists between the containers.

### **[LOW] DEP-5 — Image hygiene: mutable base tags, build toolchain in final layer, obsolete compose key**

Base images are mutable tags (`python:3.11-slim`, `node:20-slim`), not digest-pinned — builds are not reproducible and silently absorb base changes. `gcc`/`g++`/`-dev` headers are installed in the **final** stage and never removed (they exist to build wheels; lxml ships manylinux wheels, so they may be entirely unnecessary — test, then drop or split into a builder stage), inflating size and CVE surface. `version: '3.8'` in compose is deprecated/ignored by Compose v2. **Migration flag:** NO.

### **[LOW] DEP-6 — Single-container entrypoint: daemon death goes unnoticed**

[docker/entrypoint.sh](docker/entrypoint.sh) backgrounds the daemon with `&` and execs gunicorn. tini reaps the zombie, but nothing restarts the daemon or fails the container — a crashed daemon leaves a container that looks healthy and serves an RSS feed that quietly stops growing (which the broken status heuristic, ARCH-1, then can't report either). **Resolution:** simplest robust fix: trap on daemon exit (`wait -n` loop) and kill gunicorn so Docker's `restart: unless-stopped` recycles the pair; or run both under a real init (s6-overlay/supervisord); plus the DEP-2 healthcheck on the heartbeat. **Migration flag:** NO.

---

## Remediation Roadmap

Findings marked ⚙ require **coordinated daemon + RSS-server changes** — deploy order noted; everything else is independently shippable.

### Phase 1 — Critical and security (fix before next deployment)

| Order | Finding | Action | Notes |
|---|---|---|---|
| 1.1 | SEC-4/DEP-1 | Add `.dockerignore`; delete stale root `credentials.json`; `chmod 600 data/.secret_key`; rotate the secret key | Do first — every locally built image until then embeds secrets. No code change. |
| 1.2 | SEC-1 | Delete `/api/dashboard`; add `@requires_session_auth` to `/api/magnets`; document `/feed.xml` as intentionally public | Public API change — note in CHANGELOG. Frontend already uses authenticated endpoints; only `endpoints.ts` cleanup needed. |
| 1.3 | SEC-2 ⚙ | Auth/IP-filter flags read from config at request time | Ship RSS-side change first; daemon unaffected. Unblocks trusting the Settings page. |
| 1.4 | SEC-3 | Rightmost-untrusted XFF parsing + `BIND_TRUSTED_PROXIES` config key | Depends on nothing; test with the nginx and container-proxy topologies. New config key (backward-compatible default). |
| 1.5 | CQ-3 | Redact proxy credentials in logs | Two-line fix; logs are user-visible via `/api/logs`. |
| 1.6 | SEC-5 | Add `CSRF_FAILED`, `IP_BLOCKED`, `SETUP_REJECTED`, `LOGOUT`, `ACCOUNT_UNLOCKED` security events | Do alongside 1.4 so the new IP logic is observable from day one. |
| 1.7 | TEST-1 | Auth-enforcement matrix test + public-route allowlist meta-assertion | Land in the same PR as 1.2 — it locks the new auth surface in place. |

### Phase 2 — High-severity reliability and architecture

| Order | Finding | Action | Notes |
|---|---|---|---|
| 2.1 | ARCH-1 ⚙ | `daemon_heartbeat` table; daemon writes, RSS reads with mtime fallback | **Sequencing:** (a) ship schema + daemon writer + RSS reader-with-fallback in one release — old RSS ignores the new table, new RSS falls back when the row is absent, so either component can restart first; (b) remove the mtime fallback one release later. Schema migration: additive `CREATE TABLE IF NOT EXISTS`. |
| 2.2 | RES-2 | Fix transient-error classification with real library exception types + regression tests raising them | Independent. Restores the designed retry behavior. |
| 2.3 | RES-4 | Bounded drain (≤60s after SIGTERM), `cancel_futures` + hard-exit path, `TimeoutStopSec=120` in `bind.service`, `stop_grace_period: 75s` in compose | Service-file change — flag in release notes for systemd installs. |
| 2.4 | ARCH-4 | Atomic `write_config` (tmp+`os.replace`, reuse TrackerManager pattern); stop clobbering `BIND_DB_PATH` | Do before 2.5 — ARCH-2's per-tick config reads increase read frequency against the write race. |
| 2.5 | ARCH-2 ⚙ | Daemon re-reads `SCRAPING_ENABLED` per tick; delete `.enable-scraping` mechanism; daemon clears stale sentinels at startup | **Sequencing:** daemon first (it must consume the sentinel *and* read config for one release), then remove the sentinel-touch from the RSS enable endpoint. Shipping RSS-first leaves a window where enable does nothing for old daemons. |
| 2.6 | ARCH-3 | Daemon clears `.trigger` at startup; stale-trigger overwrite in the trigger route | Bundle with 2.5 (same loop code). |
| 2.7 | RES-1 | Cooldown-based proxy re-admission; only the proxy layer marks proxies failed | Independent. |
| 2.8 | DEP-2/DEP-6 ⚙ | DB-only `/health`; HEALTHCHECKs for both containers (daemon check reads the heartbeat); entrypoint fails container on daemon death | Depends on 2.1 (heartbeat). |

### Phase 3 — Medium-term refactors and quality

| Finding | Action |
|---|---|
| ARCH-5 | Thread-safe scrape-run recording (separate connection or job-thread-recorded results) |
| ARCH-6 | Drop `--interval` from compose; unify on `SCRAPE_INTERVAL` in entrypoint.sh |
| CQ-1 | Response `Protocol` for the retry engine; credentials dataclass; remove per-module mypy `disable_error_code`; drop flask/werkzeug from `ignore_missing_imports` |
| RES-5 | `RotatingFileHandler` for `bind.log`; tail-read in `/api/logs` |
| TEST-2/3/4 | CSRF cross-channel + cross-session tests; extract daemon loop body from `pragma: no cover` and integration-test sentinel handling; FTS update/delete trigger test; compose smoke test in CI (after 2.1) |
| DEP-D1/D2 | Measure cloudscraper layer success rate from logs → drop or replace; bump impersonation target + `BIND_IMPERSONATE` config |
| SEC-6 | Secret-key resolution after config load; CRITICAL log on ephemeral; `BIND_COOKIE_SECURE` option |
| SEC-7 | Per-IP lockout tracking (credentials schema v3 + migration); flock across read-modify-write |
| DEP-3 | `chown`ed data/logs dirs + `VOLUME` in images; uid-1001 docs for bind mounts |
| FE-4 | Generic client-facing error messages; log details server-side |

### Phase 4 — Deferred / low priority

- CQ-4 dead-code sweep: templates + static CSS, `requires_auth`/`check_auth`, jinja global, `get_default_trackers`, `print()`→logger; archive `data/magnets/` flat files after confirming migration completeness.
- Version skew: reconcile pyproject 2.2.0 ↔ CHANGELOG 1.2.1 **before the next git tag** (docker tag derivation).
- SEC-8/SEC-9: `compare_digest`, token rotation on login, `session.clear()` on login.
- DEP-5: digest-pinned base images; drop gcc/g++ from final layer (verify wheels); remove compose `version:` key.
- DEP-D3: deliberate bs4 4.15 / lxml 6.1.1 bumps with scraper tests; FE-2 `MagnetLink` guard component.
- RES-3 enhancement: schema-drift alert gates detail fetching for the remainder of the job.

---

*Audit complete. No fixes have been applied; every finding above includes the file/line evidence needed to implement independently.*
