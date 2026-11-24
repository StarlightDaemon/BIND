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
  versions (F7) — CI verified green (commit c752f8a, 2026-06-21)
- Wave 5-B: LiveConfig — live-reload config without daemon restart,
  env-seed pattern removed from bind.py and rss_server.py (2026-06-14)
- Waves 1-4: security hardening, config, egress, retry improvements
  (2026-06-04 through 2026-06-14)
- Remediation branch remediation/waves-4-6 merged to main and deleted
  (2026-06-14)
- Audit v4.2 run 2026-06-22 at commit 7af0456: 10 findings (F-A1 through F-A10),
  0 critical/high. F-A1 maps to deferred F6. F-A6/F-A9/F-A10 info findings —
  no action. F-A2/F-A3/F-A4/F-A5/F-A7 resolved in documentation cleanup
  commit 86b23ab. F-A8 resolved by local deletion of .venv.broken-wsl/
  (192 MB, gitignored — no commit needed).
- Serena project config and memory layer added: .serena/project.yml and
  .serena/memories/ surfaced for version control (commit a885c94, 2026-07-01).

## Open Loops

See the `## Active` section of OPEN_LOOPS.md: F-J3 open (zod 4 bump in the local validator tooling), F6 deferred (frontend tests; owner scoping). F-A6, F-A9 and F-A10 are no-action; everything else is closed (F-J2 closed 2026-11-24).
