# BIND — Current State

Last Updated: 2026-06-21

## Status

Production / Long-Term Maintenance.
Version v2.2.0 shipped 2026-06-21.

## Edict Version

1.0.0 (upgraded from v0.6.1 on 2026-06-14)

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
- Edict upgraded from v0.6.1 to v1.0.0 (2026-06-14)

## Open Loops

F1 and F7 resolved. See OPEN_LOOPS.md.

## Deferred

None at this time.
