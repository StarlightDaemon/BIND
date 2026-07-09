# BIND — Current State

## Status

Production / Long-Term Maintenance.
Version v2.2.0 shipped 2026-06-21.

## Branch

main — clean. HEAD: see git log.

## Test Suite

547 tests passing. Coverage: 94.51%.

## Recent Work

- CI health repair: ruff format violation (F1) fixed in src/rss_server.py and
  tests/test_auth_matrix.py; GitHub Actions bumped to node24-targeting major
  versions (F7) — CI verified green (commit 8ce7661, 2026-06-21)
- Wave 5-B: LiveConfig — live-reload config without daemon restart,
  env-seed pattern removed from bind.py and rss_server.py (2026-06-14)
- Waves 1-4: security hardening, config, egress, retry improvements
  (2026-06-04 through 2026-06-14)
- Remediation branch remediation/waves-4-6 merged to main and deleted
  (2026-06-14)
- Audit v4.2 run 2026-06-22 at commit 49f5138: 10 findings (F-A1 through F-A10),
  0 critical/high. F-A1 maps to deferred F6. F-A6/F-A9/F-A10 info findings —
  no action. F-A2/F-A3/F-A4/F-A5/F-A7 resolved in documentation cleanup
  commit 48376df. F-A8 resolved by local deletion of .venv.broken-wsl/
  (192 MB, gitignored — no commit needed).
- Serena project config and memory layer added: .serena/project.yml and
  .serena/memories/ surfaced for version control (commit 28d0984, 2026-07-01).

## Open Loops

See OPEN_LOOPS.md: F1–F19, F-A2–F-A10.
