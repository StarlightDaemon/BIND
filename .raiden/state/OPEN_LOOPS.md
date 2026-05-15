# Open Loops

## OL-1: Remove hard retention cap + MAX_ITEMS limit

- Status: Closed (resolved in v1.7.0, 2026-05-12)
- Closed by: `cleanup_old_files()` removed from `src/bind.py`; `MAX_ITEMS=100` cap removed from `src/rss_server.py` as part of the SQLite migration. The O(N) scan concern is resolved by FTS5 indexed search.

## OL-2: Evaluate and implement SQLite storage backend

- Status: Closed (implemented in v1.7.0, 2026-05-12)
- Closed by: `MagnetStore` with SQLite WAL + FTS5 trigram implemented in `src/core/storage.py`; flat-file storage and `history.log` / `HistoryManager` retired; one-shot migration script at `src/core/migrate.py`; 193 tests pass.
