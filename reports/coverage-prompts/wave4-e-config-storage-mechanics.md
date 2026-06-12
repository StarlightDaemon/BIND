# Wave 4-E — Config & Storage Mechanics

**Model: 🔵 Claude Sonnet**
**No dependencies** — runs independently. Must be **committed before Wave 5-B** (5-B's per-tick config reads depend on the atomic write landing first).
**Working directory:** `/Users/dante/Citadel/BIND`
**Activate the venv before any shell commands:** `source .venv/bin/activate`
**Findings remediated:** ARCH-4, RES-1, RES-5, TEST-4 from `BIND_FULL_AUDIT_REPORT.md` (repo root — read them in full first).

## Task 1 — ARCH-4: atomic config writes + stop clobbering `BIND_DB_PATH`

Two bugs in `src/config_manager.py`:

**(a) Non-atomic write.** `write_config` (`config_manager.py:160-165`) opens with `"w"` — truncating the file **before** acquiring `LOCK_EX`. A concurrent `read_config` (which takes `LOCK_SH`) landing in that window sees an empty file and silently returns all defaults.

Fix: copy the tmp-file pattern that already exists in `TrackerManager.save()` (`src/core/tracker_manager.py:64-81`): write to `<config_path>.tmp`, `flush` + `os.fsync`, then `os.replace(tmp, config_path)`. `os.replace` is atomic — readers see old-or-new, never empty. Keep `LOCK_SH` in `read_config` unchanged; the flock on the tmp file can be dropped. Clean up the tmp file on failure (again, mirror TrackerManager).

**(b) `BIND_DB_PATH` clobber.** `api_settings_post` (`src/rss_server.py:533-545`) builds `new_config` without `BIND_DB_PATH`, and `write_config` emits every `DEFAULTS` key via `settings.get(key, DEFAULTS[key])` (`config_manager.py:147-149`) — so every UI save rewrites `BIND_DB_PATH=data/bind.db`, discarding a custom DB path.

Fix at the **route**: in `api_settings_post`, start from `config_manager.read_config()` and overlay the submitted keys onto it, then pass the merged dict to `write_config`. This generalizes — any future `DEFAULTS` key not exposed in the UI is automatically preserved (Waves 4-B/4-C may add such keys). Add a regression test: write a config with `BIND_DB_PATH=/custom/bind.db`, POST settings without that key, re-read, assert the custom path survived.

## Task 2 — RES-1: proxy cooldown re-admission

`ProxyPool` (`src/core/egress_manager.py:26-48`) evicts permanently: `_failed` is a `set` only ever added to, and the manager lives for the daemon's lifetime (months). A transient ABB outage drains the whole pool — see finding RES-1 for the mechanism.

1. Replace `_failed: set[str]` with `_failed: dict[str, float]` mapping proxy → eviction monotonic timestamp.
2. `get_next()` skips a proxy only if `time.monotonic() - _failed[p] < cooldown`; expired entries are removed and the proxy re-admitted. Cooldown: module constant `PROXY_COOLDOWN_S = 1800`, overridable via env `BIND_PROXY_COOLDOWN` (no ConfigManager/UI exposure needed).
3. `__len__` counts currently-healthy proxies consistently with the new logic.
4. In `EgressManager.fetch` (`egress_manager.py:102-110`): only the **`curl_cffi_proxy`** layer's failure marks the proxy failed. Remove `cloudscraper` from the mark-failed condition — a cloudscraper failure says nothing reliable about the proxy, and today it double-marks after the proxy layer already failed.
5. Tests (append to `tests/test_egress_manager.py`): eviction skips the proxy; after cooldown expiry (mock `time.monotonic`) it is re-admitted; cloudscraper-layer failure no longer evicts.

## Task 3 — RES-5: bounded daemon log + tail-read

1. In `src/bind.py:21-28`, replace the plain `logging.FileHandler` with `logging.handlers.RotatingFileHandler(maxBytes=10 * 1024 * 1024, backupCount=3, encoding="utf-8")`. Same path, same format.
2. In `api_logs` (`src/rss_server.py:624-634`), replace `f.readlines()` of the whole file with a bounded tail-read: seek to `max(0, size - 512KB)` from the end, read, split lines, drop the first partial line when truncated, take the last 1000. Keep the response shape (`logs` reversed newest-first, `line_count`, etc.) identical — the frontend (`LogsPage.tsx`) and existing tests depend on it.
3. Tests: tail-read returns the last N lines of a file larger than the read window; small files unchanged. Existing `/api/logs` tests must pass unmodified.

## Task 4 — TEST-4: FTS trigger-sync test

No test exercises the FTS5 UPDATE/DELETE sync triggers (`magnets_au`/`magnets_ad`, `src/core/storage.py:35-41`). Append to `tests/test_storage_extended.py` one test that, on a `fresh_store`:
1. inserts a magnet titled `"alpha beta gamma"`, asserts `search("beta")` finds it;
2. issues `UPDATE magnets SET title = 'delta epsilon' WHERE info_hash = ?` directly on `store._conn`, asserts `search("epsilon")` finds it and `search("beta")` does not;
3. issues `DELETE FROM magnets WHERE info_hash = ?`, asserts both searches return empty and `SELECT count(*) FROM magnets_fts` is 0.

## Constraints

- Files in scope: `src/config_manager.py`, `src/rss_server.py` (route merge + tail-read only), `src/core/egress_manager.py`, `src/bind.py` (logging block only), tests.
- Do NOT touch `docker-compose.yml`, `docker/entrypoint.sh` (those belong to Wave 5-A), the daemon main loop, or `restart_daemon`.
- Do not change any response JSON shape.

## Verification

```bash
source .venv/bin/activate
python -m pytest tests/ -q
ruff check src/ tests/ && ruff format --check src/ tests/
mypy src/
```

## Done criteria

Full suite green including the four new test groups; `write_config` survives a mid-write reader (covered by a test that calls `read_config` against a half-written tmp scenario, or at minimum verifies `os.replace` is used — assert no `open(self.config_path, "w")` remains); custom `BIND_DB_PATH` survives a settings POST.
