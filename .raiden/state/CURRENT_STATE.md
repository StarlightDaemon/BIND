# Current State

**Last updated:** 2026-06-07
**Version:** v2.1.0
**Test suite:** 397 passed, 0 failed
**Coverage:** 97.50% (gate: 75%)
**Branch:** main (clean) — HEAD `a185e25`

---

## Project

BIND (Book Indexing Network Daemon) is a Python daemon that archives audiobook metadata from public sources, generates magnet links and RSS feeds, and serves a web UI with full-text search, metrics dashboard, and configuration panel. Production-ready; deployed via Proxmox LXC or Docker.

**Status:** Production / Long-Term Maintenance. v2 task set complete. No open feature work.

---

## Confirmed Current State

- v1.7.1 baseline: SQLite WAL+FTS5, settings UI, Docker Hub CI, secret key auto-generation.
- v2.0.0 shipped (2026-06-04): domain resilience probe, metrics dashboard, CI dev dep audit.
- v2.1.0 shipped (2026-06-04): coverage gate raised 40%→75%, storage+resilience test suites, Codecov integration.
- Coverage push session (2026-06-04): multi-agent wave system; 76.54% → 97.50% (397 tests); agent prompts at `reports/coverage-prompts/`; Wave 2 prompts (B, E) ready but not yet run.
- RAIDEN Instance installed at Edict v0.6.1.
- All v2 agent prompts archived at `.raiden/local/prompts/v2-completion/`.
- WSL→macOS migration remediation complete (2026-06-07): hook permissions fixed, CRLF stripped from 2 Python files, `/mnt/e/` paths corrected across AGENTS.md, prompt files, audit docs, and conftest.py. `.gitignore` anomaly concern investigated and confirmed NOT present.

## v2 Feature Summary

- `BindScraper.probe_target()` — classifies target as reachable/cloudflare_block/wrong_content/unreachable
- Daemon startup WARNING when target probe returns unreachable or wrong_content
- `/health` endpoint includes cached `target_probe` field (5-min TTL)
- `scrape_runs` SQLite table — daemon records result, items_new, duration_s after every cycle
- `/metrics` route — auth-gated dashboard: counts, scrape history, success rate (Vesper theme)
- CI audits both production and dev dependencies via `pip-audit`
- Coverage gate enforced at 75% in CI and local pytest runs
- Codecov badge live; upload on every CI run

## In Progress

- None. Maintenance mode only.

## Not Yet Done

- Performance tuning for very large datasets (>100k records) — not a practical concern at current scale.

## Known Constraints

- SQLite WAL mode requires local filesystem; fails on network mounts (WSL2 /mnt/, NFS, SMB). Error is raised at startup with a clear message.
- Cloudflare resistance is multi-layer (curl_cffi → cloudscraper with proxy → fallback); may need updates if upstream anti-bot measures change.
- AudioBookBay migrates domains periodically; update `ABB_URL` in config when this occurs. probe_target() will log a WARNING when the domain changes.
