# Current State

**Last updated:** 2026-05-12  
**Test suite:** 174 passed, 0 failed  
**Branch:** main (clean)

---

## Architecture audit complete (2026-05-12)

All 9 "Do Soon" recommendations (R1–R9) and R10 from the architecture audit
are implemented. Full report at `reports/architecture_audit_2026-05-12.md`.

R11 (storage layer abstraction) is held for operator review — see OL-2 in
`OPEN_LOOPS.md`.

## Active open loops

- **OL-1** — Remove 90-day retention cap + MAX_ITEMS=100 limit (BLOCKED on OL-2)
- **OL-2** — Evaluate and implement SQLite storage backend (BLOCKS OL-1, held for operator review)

## What not to touch until OL-2 is resolved

- `cleanup_old_files()` in `src/bind.py` — operator wants this removed/made optional, but not until the database question is settled
- `MAX_ITEMS = 100` in `src/rss_server.py` — same hold
- `search_magnets()` in `src/rss_server.py` — O(N) scan; acceptable now, becomes a problem if OL-1 ships without OL-2
