# Open Loops

---

## OL-1: Remove hard retention cap + review storage backend (BLOCKED on OL-2)

**Opened:** 2026-05-12  
**Status:** Held for operator review — do not implement until OL-2 is decided

**What the operator wants:**
- Remove or make the 90-day file retention policy optional. The operator wants BIND to be a permanent archive, not a rolling window.
- Remove or make configurable the `MAX_ITEMS=100` cap in `read_magnets()` / `feed()`.

**Current behaviour to change:**
- `cleanup_old_files()` in `src/bind.py` deletes `magnets_*.txt` files older than 90 days. This is called on every job run.
- `MAX_ITEMS = 100` in `src/rss_server.py` hard-caps the RSS feed and dashboard at 100 items.
- The 90-day cap is what keeps `search_magnets()` O(N) scan fast (~2,700 records max). Removing it makes the dataset grow unboundedly.

**Why this is blocked on OL-2:**
Removing the retention cap without a database means `search_magnets()` scans every record on every search request indefinitely. At 30 releases/day with no cleanup, the scan reaches ~55,000 records (~40MB) after 5 years. This is the exact condition that makes R11 (SQLite) necessary — not a theoretical future concern but an immediate consequence of this change.

**Do not implement OL-1 without first resolving OL-2.**

---

## OL-2: Evaluate and implement SQLite storage backend (BLOCKS OL-1)

**Opened:** 2026-05-12  
**Status:** Held for operator review — design decision required before any work begins

**What needs a decision:**
The operator wants to understand the database options before committing. This is the right order: decide on storage first, then remove the retention cap.

**Context (from architecture audit 2026-05-12):**
The flat-file model is correct for the current 90-day rolling window. Removing that window makes `search_magnets()` a full-table scan with no index, growing linearly forever. SQLite resolves this and also unlocks query flexibility (date filtering, faceted search, source attribution) that flat files cannot provide.

**Recommended approach when ready:**
1. Define a `StorageBackend` protocol: `add()`, `exists()`, `get_recent()`, `search()`
2. Wrap current flat-file code as `FlatFileBackend` — zero behaviour change, all tests pass
3. Implement `SQLiteBackend` using stdlib `sqlite3` with WAL mode (no new dependency)
4. Select via `BIND_STORAGE_BACKEND=sqlite|flatfile` env var, default `flatfile`
5. Write a one-shot migration script: reads all `magnets_*.txt` → inserts into SQLite
6. Once SQLite backend is validated, OL-1 (retention removal) can be implemented safely

**Design notes for the implementing agent:**
- SQLite WAL mode handles concurrent reads (RSS server) + single writer (daemon) correctly
- `history.log` / `HistoryManager` can remain flat-file — it is append-only and only read at startup; no query flexibility needed
- `TrackerManager` can remain flat-file — it is a single-record JSON store
- The migration from flat-file → SQLite should be non-destructive: keep `magnets_*.txt` files until the operator confirms the migration is complete
- `MAX_ITEMS=100` in the RSS feed should become a configurable `BIND_FEED_LIMIT` env var with a sensible default (100 is fine for RSS clients; the web UI `/magnets` page uses `search_magnets()` with pagination so it is unaffected)

**Files this will touch:**
- `src/rss_server.py` — `read_magnets()`, `search_magnets()`, `MAX_ITEMS`
- `src/bind.py` — `cleanup_old_files()`, job integration
- New: `src/core/storage.py` — `StorageBackend` protocol + both backends
- New: `scripts/migrate_to_sqlite.py` — one-shot migration
- `tests/` — new test file for storage backends
