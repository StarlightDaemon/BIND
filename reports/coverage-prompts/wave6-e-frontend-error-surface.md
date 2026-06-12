# Wave 6-E — Frontend Hardening & Server Error Surface

**Model: 🔵 Claude Sonnet**
**Dependencies:** none. Avoid running concurrently with prompts editing `src/rss_server.py` (4-A/4-C/5-B) — sequence after whichever of those are in flight.
**Working directory:** `/Users/dante/Citadel/BIND`
**Activate the venv before any shell commands:** `source .venv/bin/activate`
**Findings remediated:** FE-2, FE-4 from `BIND_FULL_AUDIT_REPORT.md` (repo root — read both first).

## Task 1 — FE-2: defense-in-depth magnet link component

Magnet hrefs are currently safe by server-side construction (scheme is fixed, hash is validated hex, title is `quote_plus`-encoded), but two pages render `<a href={row.magnet}>` directly — a future refactor that builds hrefs client-side from raw fields would silently become an XSS vector.

1. New component `frontend/src/components/MagnetLink.tsx`:
   ```tsx
   const MAGNET_PREFIX = 'magnet:?xt=urn:btih:';
   ```
   Renders the styled `<a>` when `href.startsWith(MAGNET_PREFIX)`; otherwise renders the same visual as a disabled non-link element (no `href` at all — not `href="#"`), with `title="Invalid magnet link"`. Accept `children` and `style` so both call sites keep their existing appearance.
2. Replace the two raw anchors: `DashboardPage.tsx` rowActions (`:259-272`) and `MagnetsPage.tsx` rowActions (`:116-123`).
3. Match the existing code style: inline `React.CSSProperties` constants, fujin CSS variables, no new dependencies.

## Task 2 — FE-4: stop forwarding raw exception text to clients

The fetch wrapper is fine (it only surfaces `body.error ?? body.message`); the **server** puts raw exception strings — including absolute filesystem paths from `OSError` — into those fields. Fix each site in `src/rss_server.py`: log the full exception server-side (`logger.error(..., exc_info=True)` or message-level as appropriate), return a generic client message:

| Site | Current | Replace client message with |
|---|---|---|
| `api_settings_trackers` (`:589`) | `f"Failed to update trackers: {e}"` | `"Failed to update trackers — see server log."` **except** keep validation messages: `set_trackers_from_text` failures from *invalid input* should still tell the user what was wrong. Distinguish: catch `OSError` → generic; other exceptions raised by normalize/validation → pass through (read `tracker_manager.py` to see what actually raises). |
| `api_trigger_scrape` (`:661`) | `f"Could not write trigger file: {e}"` | `"Could not write trigger file — see server log."` |
| `api_logs` (`:632`) | `f"Error reading log file: {e}"` (in the logs array) | `"Error reading log file — see server log."` |
| `check_daemon_status` (`:278`) | `f"Error checking status: {str(e)}"` (reaches the dashboard status line) | `"Error checking daemon status"` + `logger.warning` with the detail |
| `api_setup` (`:408-410`) | embeds `write_msg` | keep — `write_config` messages are already user-facing validation text, not exceptions; verify and leave as-is |

Audit the rest of `rss_server.py` for any other `{e}` interpolation into a response and apply the same pattern; list what you found.

## Task 3 — tests

- `MagnetLink`: no frontend test runner exists (`package.json` has no test script) — do NOT introduce one; `npx tsc --noEmit` is the gate, plus a manual-check note in your summary.
- Backend: existing tests asserting on the old message strings (`grep -rn "disk full\|Could not write" tests/`) — update those assertions to the new generic messages; add one test asserting an `OSError` path's response contains no filesystem path (assert `tmp_path` string not in body).

## Constraints

- No new npm dependencies; no new Python dependencies.
- Response JSON *shapes* unchanged (keys/status codes) — only message text changes.
- Do not touch auth, CSRF, or settings-merge logic in the routes you edit.

## Verification

```bash
source .venv/bin/activate
python -m pytest tests/ -q
ruff check src/ tests/
cd frontend && npx tsc --noEmit && npm run build && cd ..
```

## Done criteria

Both anchors render through `MagnetLink`; a non-`magnet:` href renders dead; no route response can contain raw `OSError` text (grep `src/rss_server.py` for `: {e}` interpolations into user-facing strings → only validation passthroughs remain, each justified); suite + frontend build green.
