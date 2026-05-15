# Current State

**Last updated:** 2026-05-15
**Version:** v1.7.1
**Test suite:** 193 passed, 0 failed
**Branch:** main (clean)

---

## Project

BIND (Book Indexing Network Daemon) is a Python daemon that archives audiobook metadata from public sources, generates magnet links and RSS feeds, and serves a web UI with full-text search. Production-ready; deployed via Proxmox LXC or Docker.

**Status:** Production / Active Maintenance.

---

## Confirmed Current State

- Architecture audit completed (2026-05-12): recommendations R1–R10 implemented; R11 (storage abstraction) resolved as part of v1.7.0.
- v1.7.0 shipped: flat-file storage replaced by SQLite (`MagnetStore`, WAL + FTS5 trigram); 90-day retention cap removed; `MAX_ITEMS=100` cap removed; one-shot migration script included.
- v1.7.1 shipped: Docker Hub CI, automatic secret key generation, cloudscraper proxy fallback, settings UI at `/settings`.
- RAIDEN Instance installed at Edict v0.4.0.

## In Progress

- Ongoing maintenance; no active feature branches at this time.

## Not Yet Done

- Performance tuning for very large datasets (post-SQLite, the O(N) scan constraint is removed; no active work scheduled).

## Known Constraints

- SQLite WAL mode handles concurrent RSS server reads and daemon writes correctly; no external database dependency.
- Cloudflare resistance is multi-layer (curl_cffi → cloudscraper with proxy → fallback); may need updates if upstream anti-bot measures change.
