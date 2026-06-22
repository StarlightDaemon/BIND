# Decisions

## D-001

- Date: 2026-05-12
- Status: Active
- Decision: architecture audit recommendations R1–R10 are implemented; R11 (storage layer abstraction) is deferred pending operator review of the database question.
- Rationale: the flat-file model is correct for the rolling-window use case but becomes O(N) at scale if the retention cap is removed. R11 requires a decision on persistence backend before removal of the cap is safe.

## D-002

- Date: 2026-05-12 (resolved in v1.7.0)
- Status: Active
- Decision: SQLite (WAL + FTS5 trigram) replaces flat-file storage as the sole persistence backend; the 90-day retention cap and `MAX_ITEMS=100` limit are removed.
- Rationale: SQLite resolves the scalability constraint blocking removal of the retention cap (OL-2 unblocks OL-1). FTS5 trigram search replaces the O(N) `search_magnets()` scan. WAL mode handles concurrent reads (RSS server) and single writer (daemon) without locking.
- Implementation: `src/core/storage.py` (MagnetStore), `src/core/migrate.py` (one-shot migration); `cleanup_old_files()` and `MAX_ITEMS` removed from `bind.py` and `rss_server.py`.

## D-003

- Date: 2026-05-12 (shipped in v1.7.1)
- Status: Active
- Decision: settings are configurable via a browser UI at `/settings`; no file editing required for common operational parameters.
- Rationale: reduces operator friction for production deployments; centralizes configuration away from env-var-only or file-edit patterns.

## D-004

- Date: 2026-06-22
- Status: Deferred
- Decision: defer consolidation of the two Dockerfiles into a single canonical file.
- Context: BIND maintains two Dockerfiles for two distinct deployment topologies. The root Dockerfile supports the dual-container docker-compose model, where bind-daemon and bind-rss run as separate services with CMD overridden per service. The docker/Dockerfile.single supports the single-container production model, where tini acts as PID 1 and docker/entrypoint.sh supervises both processes under a single container with HEALTHCHECK wired. The production image published to Docker Hub is always built from docker/Dockerfile.single via .github/workflows/docker-publish.yml. The root Dockerfile is used for local compose development only.
- Rationale: consolidation would require docker/entrypoint.sh to become mode-aware, conditionally launching one or both processes based on an environment variable, and docker-compose.yml to be refactored accordingly. The production artifact is already hardened via docker/Dockerfile.single and the operational risk of consolidation does not justify the work at this time. Deferred pending an operator decision on whether parity between the local compose image and the published production image is a priority.
