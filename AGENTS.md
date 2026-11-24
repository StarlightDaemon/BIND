# BIND

BIND (Book Indexing Network Daemon) is a self-hosted audiobook metadata archiver: a scraping daemon that stores releases in SQLite (FTS5 search) and serves an RSS 2.0 feed, a web UI, a metrics dashboard and a settings page, with built-in authentication. Version 2.2.0, in production and long-term maintenance. It is a public GitHub repository (StarlightDaemon/BIND); a Docker image is published from it.

## Run and test

Python 3.10+ (CI tests 3.10, 3.11 and 3.12).

- Install: `pip install -r requirements-dev.txt` (or `uv sync --extra dev`; `uv.lock` is tracked)
- Test: `python -m pytest` (the coverage gate `--cov-fail-under=75` is set in `pyproject.toml`)
- Lint and format: `ruff check src/ tests/` and `ruff format --check src/ tests/`
- Type check: `mypy src/`
- Dependency audit: `pip-audit -r requirements.txt` and `pip-audit -r requirements-dev.txt`

The code imports `fcntl`, so the pytest suite runs only on Linux or macOS; on Windows, collection fails with `No module named 'fcntl'` (ruff still works). CI (`.github/workflows/ci.yml`, Ubuntu) runs all of the above on every push and pull request. `docker-publish.yml` builds and publishes the Docker image.

Test notes: `tests/conftest.py` sets `BIND_AUTH_ENABLED=false`, so `@requires_auth` passes every request in tests. `src/security.py` reads `CREDENTIALS_FILE` at import time, so any test touching credentials must monkeypatch `src.security.CREDENTIALS_FILE` to `tmp_path`.

## Layout

- `src/`: the daemon (`bind.py`), RSS and web server (`rss_server.py`), config, security, health check; `src/core/` holds scraping, storage, retry and egress
- `tests/`: the pytest suite
- `frontend/`: the TypeScript/Vite frontend (no tests yet; see F6)
- `docker/`, `Dockerfile`, `docker-compose.yml`, `deployment/`, `unraid/`: container and deployment files. Root `Dockerfile` is the two-service compose image; `docker/Dockerfile.single` is the single-container production image (D-004)
- `scripts/`: Proxmox LXC and Linux installers
- `docs/`: user and maintainer documentation
- `reports/coverage-prompts/`: past prompt files for coverage waves (history; new agent prompts go here as `wave<N>-<letter>-<topic>.md`)
- `.raiden/state/`: the project records (see below)

## Key rules

- Main branch is `main`. Agent work goes on `<agent>/<task>` branches in their own worktrees.
- No `Co-Authored-By` or other agent attribution lines in commits; the `commit-msg` hook enforces this. Never bypass it.
- Pushing to `main` runs CI and can publish a Docker image. See Standing delegation v1 in AGENTS.md.
- Never commit secrets or runtime data. `data/credentials.json`, `data/.secret_key`, logs and `.governance/` are gitignored; keep them that way. Only `config.env.example` is tracked; never commit a filled-in config.
- Don't edit `.raiden/writ/` or `.raiden/instance/`. They're historical RAIDEN v2 text kept for the old tooling. Where they, `.raiden/README.md` or `.raiden/local/` disagree with this file, this file wins. Model names and routing advice in `.raiden/local/rules/` are out of date; ignore them.

## Project records

This file and `.raiden/state/` are authoritative for this repo. Read in this order and stop when you have what you need:
1. `.raiden/state/CURRENT_STATE.md`: version, test baseline and recent work.
2. The `## Active` section at the top of `.raiden/state/OPEN_LOOPS.md`: open, deferred and held items (statuses: `open`, `deferred`, `held: <who>`, `no-action`, `accepted`, `closed`).
3. Only when needed: `DECISIONS.md` (IDs `D-0xx`), `WORK_LOG.md` and `docs/audits/` (history and evidence). Recent audit output (`.audits/`, `audit-reports/`, `.raiden/state/AUDIT_LOG.md`, `.raiden/state/last-audit.md`) is gitignored, so it exists only in the main checkout, not in fresh clones or worktrees.

Current picture: two open items and one deferred item. **F-J3** (open) is a local developer-tool risk: the untracked governance validator depends on zod 3, which has one high npm advisory that only a major bump to zod 4 fixes (F-J2, the diverged lockfiles with a critical advisory, was closed 2026-11-24). It doesn't ship and doesn't run in CI. **F-J4** (open) is similar: `uv.lock` still pins soupsieve 2.10 for Python below 3.11.5, with three advisories that only a newer Python can fix; it's not in the Docker image or CI. **F6** (deferred) is a product gap: the frontend has no tests, waiting on a scoping conversation with the owner. Three audit findings (F-A6, F-A9, F-A10) are `no-action` information only. Everything else is `closed`.

Update `CURRENT_STATE.md` and `OPEN_LOOPS.md` when you finish or pause work. Keep one home per fact and link evidence; don't paste it in. Never renumber or reuse a loop or decision ID. Medium+ audit findings become loops.

## Working in parallel

One agent per worktree. Before starting, read the Claims section of `../../HANDOFF.md` (the workspace folder two levels above the repo or worktree root, outside Git, so every worktree sees the same file) and `git worktree list`, then add your claim line there; mark it done when you finish. Separate tasks may run in parallel only when both claims are listed there and they don't touch the same files. The owner (or the agent they assign) merges branches and updates `.raiden/state/`. Releases, deployments, the hook and Git config are one-at-a-time work.

This repository is public: don't commit personal names, absolute local paths or details of the owner's private tooling.

## Standing delegation v1 (operator: StarlightDaemon)
Applies to every agent working in this repo: Claude Code, Codex, Gemini CLI.

Do without asking, then report once at the end of the task:
- Read, build, test, lint. Wait for CI yourself; don't hand back "pending".
- Create agent branches (claude/*, codex/*, gemini/*); commit, rebase,
  fast-forward and merge them. Create agent worktrees.
- Push agent branches (never force). Open and update PRs; enable auto-fix.
- Merge a PR into the default branch when all checks pass, no review
  requests changes, and the merge doesn't publish (see Publication surface).
- Delete agent branches, local and remote, once their commits are in the
  default branch or another pushed branch.
- Keep records current: HANDOFF, OPEN-LOOPS, CHANGELOG and any doc that
  describes branch or PR state.

Ask once, in one message listing everything pending:
- Tags, releases, leaving a -dev version, or any merge that publishes.
- Force push, or rewriting history that's already pushed.
- Any other deletion: worktrees, backup refs, files or branches an agent
  didn't create, commits that exist nowhere else.
- Committing, moving or discarding StarlightDaemon's uncommitted work.
- CI workflows, branch protection, repo settings, secrets, agent permission
  settings, and this section.
- Anything against live hosts, services or devices.

Stop and report: failing checks you can't fix within the task, conflicts in
files StarlightDaemon is editing, or anything this section doesn't cover.

### Publication surface
Merging to `main` publishes: `.github/workflows/docker-publish.yml` pushes the `starlightdaemon/bind:latest` image on every push to `main` (and version images on `v*` tags). Every merge to `main` is gated.
