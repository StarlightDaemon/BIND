# BIND Fujin Migration — Startup Completion

**Prepared by:** Claude Sonnet 4.6 (external session, 2026-06-04)  
**Scope:** Fix two small issues left after the migration, verify the app runs end-to-end, build for production, commit, and push.

---

## Background

A full React/Mantine/Fujin migration has been completed on the `main` branch. Read this before touching anything:

- `src/rss_server.py` has been rewritten. All 6 Jinja2 template routes are gone. In their place: JSON API endpoints at `/api/*`, session-based auth (replacing HTTP Basic Auth), `X-CSRF-Token` header protocol for POST requests, and a SPA catch-all route that serves `src/static/dist/index.html`.
- `frontend/` contains a Vite + React 18 + TypeScript + Mantine v7 + React Router v6 application. Fujin components are vendored at `frontend/src/fujin/`.
- 7 page components exist: Dashboard, Magnets, Metrics, Settings, Logs, Setup, Login.
- 400 Python tests pass at 95.94% coverage. Do not break them.
- The Jinja2 templates in `src/templates/` are now dead code. Do not delete them — they are not tracked and removing them is out of scope.

---

## Fix 1 — Remove unused `navigate` in App.tsx

`frontend/src/App.tsx` imports `useNavigate` and assigns it to `navigate`, but only `<Navigate>` JSX components are used for redirects. The `navigate` variable is never called, and `void navigate` is a no-op suppression line.

**Remove both lines:**
```tsx
// Remove this import member:
useNavigate,          // in the react-router-dom import

// Remove these two lines inside AppRoutes():
const navigate = useNavigate();
void navigate; // suppress unused warning from strict mode
```

After editing, run:
```bash
cd /mnt/e/BIND/frontend && npx tsc --noEmit
```

Confirm zero errors before continuing.

---

## Fix 2 — Update .gitignore

Add these two entries to `/mnt/e/BIND/.gitignore` under the existing "BIND Project" section:

```
# Fujin frontend
frontend/node_modules/
src/static/dist/
```

`frontend/node_modules/` must never be committed. `src/static/dist/` is the Vite build output — it is generated, not authored.

---

## Dev Server Smoke Test

You need two terminals.

**Terminal 1 — Flask (port 5001):**
```bash
cd /mnt/e/BIND
source .venv/bin/activate
BIND_AUTH_ENABLED=false BIND_DB_PATH=data/bind.db flask --app src.rss_server run -p 5001
```

**Terminal 2 — Vite (port 5173):**
```bash
cd /mnt/e/BIND/frontend
npm run dev
```

Open `http://localhost:5173` in a browser. Verify each of these:

| Check | Expected |
|---|---|
| `http://localhost:5173/` | Dashboard renders with KPI tiles and Recent Index table |
| `http://localhost:5173/magnets` | Magnets page with search bar |
| `http://localhost:5173/metrics` | Metrics page with 5 KPI tiles |
| `http://localhost:5173/settings` | Settings page with 3 form sections |
| `http://localhost:5173/logs` | Logs page with Security/Daemon tabs |
| `http://localhost:5173/setup` | Setup page with BIND SVG icon and create-account form |
| `http://localhost:5173/login` | Login page with wordmark and sign-in form |
| `GET http://localhost:5001/api/dashboard` | JSON with `magnet_count`, `magnets`, `system_status` |

If any page is blank or throws a React error, open the browser console and report the exact error. Do not guess — read it.

---

## Auth Flow Test

Stop Flask. Restart it **without** `BIND_AUTH_ENABLED=false`:
```bash
BIND_DB_PATH=data/bind.db flask --app src.rss_server run -p 5001
```

Verify:
1. `http://localhost:5173/metrics` redirects to `/login` (React Router guard in `App.tsx`).
2. Logging in with valid credentials redirects to `/`.
3. The "Sign out" button in the ToolShell footer clears the session and redirects to `/login`.
4. After logout, `GET /api/me` returns `{"authenticated": false, "auth_enabled": true}`.

If step 2 fails with a 403 on the login POST, the CSRF token flow is broken. The `apiFetch` function in `frontend/src/api/client.ts` calls `GET /api/csrf-token` before every non-GET request — confirm this request appears in the network tab before the login POST.

---

## Production Build Test

```bash
cd /mnt/e/BIND/frontend && npm run build
```

This runs `tsc --noEmit` first, then Vite. Expected output: `src/static/dist/` is created containing `index.html` and an `assets/` directory.

With only Flask running (no Vite), open `http://localhost:5001`. The SPA should load from the built files. If it loads but assets 404, check that Vite's `base` in `vite.config.ts` matches how Flask serves static files (`/static/dist/`).

---

## Python Tests

Run the full suite to confirm nothing is broken:
```bash
cd /mnt/e/BIND
source .venv/bin/activate
python -m pytest tests/ -q
```

Expected: 400 passed, ≥75% coverage. If any test regresses due to Fix 1 (App.tsx is TypeScript — Python tests are unaffected), investigate before continuing.

---

## Commit

Stage all new and modified files. Do not stage `frontend/node_modules/` or `src/static/dist/`. The staged set should be:

```
frontend/package.json
frontend/package-lock.json
frontend/tsconfig.json
frontend/vite.config.ts
frontend/index.html
frontend/src/**
src/rss_server.py
tests/test_rss_server.py
tests/test_metrics.py
.gitignore
```

Commit message (concise, describe the migration):
```
feat: migrate UI to React + Mantine v7 + Fujin component library

Replace all Jinja2 templates and the hand-rolled Carbon CSS with a
Vite/React SPA. Flask becomes a JSON API server. Session-based auth
replaces HTTP Basic Auth. All 400 tests pass at 95.94% coverage.
```

---

## Push

Use the instance PAT following the standard push protocol. Log out of the PAT immediately after the push completes.
