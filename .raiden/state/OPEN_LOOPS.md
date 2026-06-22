# BIND — Open Loops

## F1 — ruff format CI failure [resolved-pending-CI-verification]

- **Opened:** 2026-06-08 (CI red since this date)
- **Cause:** `ruff format` drift in `src/rss_server.py` and `tests/test_auth_matrix.py`
- **Fix applied:** 2026-06-21 — ran `uv run ruff format src/ tests/`; both files
  reformatted, `ruff check src/ tests/` passes with no issues
- **Status:** resolved-pending-CI-verification — changes not yet pushed

## F7 — node20 GitHub Actions deprecation [resolved-pending-CI-verification]

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
- **Status:** resolved-pending-CI-verification — changes not yet pushed
