# BIND — Open Loops

## F1 — ruff format CI failure [resolved]

- **Opened:** 2026-06-08 (CI red since this date)
- **Cause:** `ruff format` drift in `src/rss_server.py` and `tests/test_auth_matrix.py`
- **Fix applied:** 2026-06-21 — ran `uv run ruff format src/ tests/`; both files
  reformatted, `ruff check src/ tests/` passes with no issues
- **Status:** resolved — commit 8ce7661, 2026-06-21

## F7 — node20 GitHub Actions deprecation [resolved]

- **Opened:** June 2026 (forcing deadline: ~2026-06-16)
- **Cause:** all actions in ci.yml and docker-publish.yml pinned to node20-era
  major versions
- **Fix applied:** 2026-06-21 — bumped to node24-targeting major versions:
  - `actions/checkout` v4 → v7
  - `actions/setup-python` v5 → v6
  - `codecov/codecov-action` v4 → v7
  - `docker/login-action` v3 → v4
  - `docker/build-push-action` v6 → v7
  - `docker/metadata-action` v5 → v6
  - `docker/setup-buildx-action` v3 → v4
- **Status:** resolved — commit 8ce7661, 2026-06-21

## F8 — GitHub Actions pinned to mutable major tags [resolved]

- **Opened:** as part of T3 audit
- **Cause:** all 7 actions in CI/build pipelines pinned to major versions that
  can update at minor/patch level without change to workflow YAML
- **Fix applied:** 2026-06-22 — SHA-pinned all 7 actions to immutable commit
  SHAs (e.g., `actions/checkout@<full-SHA>` instead of `v4`)
- **Status:** resolved — commit 3d183c6, 2026-06-22

## F9 — esbuild advisory GHSA-g7r4-m6w7-qqqr [resolved]

- **Opened:** as part of T1 audit
- **Cause:** esbuild dependency vulnerable to arbitrary code execution;
  advisory recommended >=0.28.1
- **Fix applied:** 2026-06-22 — added npm overrides block to package.json
  forcing esbuild >=0.28.1 regardless of transitive dependency versions
- **Status:** resolved — commit 4209044, 2026-06-22

## F10 — config keys missing from config.env.example [resolved]

- **Opened:** as part of T1 audit
- **Cause:** four config keys (SCRAPING_ENABLED, BIND_TRUSTED_PROXIES,
  BIND_PROXY_COOLDOWN, BIND_COOKIE_SECURE) read by the application but absent
  from the example config file, blocking accurate operator onboarding
- **Fix applied:** 2026-06-22 — added all four keys to config.env.example with
  comments, types, defaults, and explanatory text matching existing style:
  - SCRAPING_ENABLED: boolean, default true (controls scraper enable/disable)
  - BIND_PROXY_COOLDOWN: integer seconds, default 1800 (proxy reuse cooldown)
  - BIND_TRUSTED_PROXIES: CIDR list, default 127.0.0.1/32,::1/128 (X-Forwarded-For trust)
  - BIND_COOKIE_SECURE: boolean, default false (HTTPS-only cookie flag)
- **Status:** resolved — this session, 2026-06-22

## F11 — stale merged branch feat/v2-completion [resolved]

- **Opened:** as part of T4 housekeeping audit
- **Cause:** feature branch merged to main but not deleted from local/remote
  tracking; clutters branch list
- **Fix applied:** 2026-06-22 — deleted feat/v2-completion locally via git
  branch -d
- **Status:** resolved — commit 4bb7316, 2026-06-22

## F12 — uv.lock and other tool files untracked [resolved]

- **Opened:** as part of T3 audit
- **Cause:** uv.lock, skills-lock.json, and tool directories (.claude/,
  .serena/, .audits/) ignored in .gitignore despite being part of the
  project's reproducible build/tooling state
- **Fix applied:** 2026-06-22 — added uv.lock to tracked files; added .claude/,
  .serena/, skills-lock.json, .audits/ to .gitignore in a single pass
- **Status:** resolved — commit 3d183c6, 2026-06-22

## F13 — stale Dependabot PR #2 [resolved]

- **Opened:** as part of T4 housekeeping audit
- **Cause:** Dependabot auto-PR to bump pytest to 9.0.3 has been open for
  weeks; pytest already at 9.0.3 in pyproject.toml
- **Fix applied:** 2026-06-22 — closed PR #2 as stale; no code change needed
- **Status:** resolved — commit 4bb7316, 2026-06-22

## F14 — BIND_FULL_AUDIT_REPORT.md at repo root [resolved]

- **Opened:** as part of T1 audit
- **Cause:** large audit report committed to repo root; should not persist in
  version control (audit artifacts belong in reports/coverage-prompts/ if
  needed; production code should not reference them)
- **Fix applied:** 2026-06-22 — removed BIND_FULL_AUDIT_REPORT.md via git rm
- **Status:** resolved — commit 4bb7316, 2026-06-22

## F15 — nested data/magnets/magnets/ directory [resolved]

- **Opened:** as part of T1 audit
- **Cause:** data/magnets/magnets/ double-nesting appeared suspicious (possible
  accidental nested directory creation or symlink issue)
- **Fix applied:** 2026-06-22 — diagnostic investigation confirmed not-a-bug;
  the nesting is a pre-SQLite artifact retained from an earlier data structure
  and no code references the nested path; safe to leave as-is
- **Status:** resolved — no commit needed; documented as non-issue, 2026-06-22

## F16 — tool dirs .claude/ and .serena/ untracked [resolved]

- **Opened:** as part of T3 audit
- **Cause:** local tool directories untracked; parallel to F12 (uv.lock,
  skills-lock.json)
- **Fix applied:** 2026-06-22 — added .claude/ and .serena/ to .gitignore in
  same pass as F12
- **Status:** resolved — commit 3d183c6, 2026-06-22

## F17 — Python test suite not executed locally [resolved]

- **Opened:** as part of T1 audit
- **Cause:** audit context was macOS post-WSL2-migration; Python test suite
  expected to run locally but previously only tested in CI
- **Fix applied:** 2026-06-22 — no code change; remote CI verified passing; local
  testing now confirmed working post-migration
- **Status:** resolved — no commit needed; migration confirmed functional,
  2026-06-22

## F18 — obsolete version: 3.8 field in docker-compose.yml [resolved]

- **Opened:** as part of T4 housekeeping audit
- **Cause:** docker-compose.yml had leftover version field set to 3.8; current
  compose schemas do not enforce versioning this way; field is vestigial
- **Fix applied:** 2026-06-22 — removed version: 3.8 line from
  docker-compose.yml
- **Status:** resolved — commit 4bb7316, 2026-06-22

## F19 — two Dockerfiles diverging without documentation [resolved]

- **Opened:** as part of T3 audit
- **Cause:** `Dockerfile` (root, dual-container compose setup) and
  `docker/Dockerfile.single` (single-container production image) diverged
  in structure and tooling without topology comments or decision record
  explaining the split
- **Fix applied:** 2026-06-22 — added topology comment blocks to both files
  explaining intent (compose: two-service runtime; single: self-contained
  production image); added D-004 entry to DECISIONS.md deferring
  consolidation to future refactor pending scoping
- **Status:** resolved — commit 3d183c6, 2026-06-22

## F-Info — .audits/ not gitignored [resolved]

- **Opened:** as part of T3 audit (informational finding)
- **Cause:** .audits/ directory (audit run artifacts) untracked and not in
  .gitignore; parallel to F12/F16
- **Fix applied:** 2026-06-22 — added .audits/ to .gitignore in same pass as
  F12/F16
- **Status:** resolved — commit 3d183c6, 2026-06-22

## F6 — frontend zero tests [open, deferred]

- **Opened:** as part of T1 audit
- **Cause:** 29 TypeScript/TSX files in the frontend codebase with zero test
  coverage; no test infrastructure (runner, fixtures, assertion libraries) in
  place; investment is significant
- **Deferred:** pending scoping conversation on test runner setup (Jest, Vitest,
  other), fixture patterns, and integration with CI. Sprawling effort requiring
  test infrastructure before any handoff prompt for coverage expansion can be
  authored.
- **Status:** open, deferred 2026-06-22 — scoping conversation required
