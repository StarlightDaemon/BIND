# Wave 6-D — Dependency Bumps & Container Image Hygiene

**Model: 🔵 Claude Sonnet**
**Dependencies:** Wave 5-A committed (it edits `docker-compose.yml`, `docker/Dockerfile.single`, and `docker/entrypoint.sh` — this prompt touches the same files and must build on its versions).
**Working directory:** `/Users/dante/Citadel/BIND`
**Activate the venv before any shell commands:** `source .venv/bin/activate`
**Findings remediated:** DEP-D2, DEP-D3, DEP-3, DEP-5 from `BIND_FULL_AUDIT_REPORT.md` (repo root — read them first).

## Task 1 — DEP-D2: current Chrome impersonation target

`EgressManager` hardcodes `impersonate="chrome120"` (`src/core/egress_manager.py:63`) — a TLS fingerprint from late 2023 that no live Chrome population presents anymore (itself an anomaly signal to Cloudflare).

1. Discover the newest target curl_cffi 0.15.0 supports: `python -c "from curl_cffi.requests.impersonate import ..."` — inspect the actual module/enum in the venv rather than guessing; list available `chromeNNN` targets in your summary.
2. New env var `BIND_IMPERSONATE`, default = the newest supported chrome target. Read at `EgressManager.__init__`; validate against the supported set with a warning + fallback to default on an unknown value (don't crash the daemon over a typo).
3. Also apply to the `probe_target` path if it constructs its own session (read `src/core/scraper.py` as it now stands).
4. Document in `docs/CONFIGURATION.md` env-var section. Test: constructing `EgressManager` with `BIND_IMPERSONATE=bogus` falls back and warns.

## Task 2 — DEP-D3: deliberate minor bumps

1. `beautifulsoup4` 4.12.3 → latest 4.15.x and `lxml` 6.1.0 → 6.1.1 in **both** `requirements.txt` and `pyproject.toml` `[project.dependencies]` (keep them in sync — they currently are).
2. bs4 4.13 changed some typing/encoding behaviors — the scraper parse tests are the canary: run `pytest tests/test_scraper.py tests/test_scraper_probe.py -q` first, then the full suite. If a bs4 behavior change breaks a parse strategy, fix the *strategy* minimally and flag it prominently in your summary; do not pin back down without trying.
3. `types-beautifulsoup4` in requirements-dev.txt: bump to the matching version.

## Task 3 — DEP-3: image user/permission fixes

In **both** `Dockerfile` and `docker/Dockerfile.single`:
1. After the `useradd` and before `USER bind`:
   ```dockerfile
   RUN mkdir -p /app/data /app/logs && chown -R bind:bind /app/data /app/logs
   ```
2. Add `VOLUME /app/data` (anonymous volume beats a crash when run without `-v`).
3. `unraid/bind.xml`: extend the Data Volume `<Config>` description to state the container runs as uid 1001 and host paths must be writable by it.
4. `docs/TROUBLESHOOTING.md`: short entry for the PermissionError-at-startup symptom → chown guidance.

## Task 4 — DEP-5: base pinning and final-layer slimming

1. **Digest-pin all four base references** (two stages × two Dockerfiles): `FROM python:3.11-slim@sha256:...` / `FROM node:20-slim@sha256:...`. Resolve current digests via `docker manifest inspect` if docker is available locally; if not, fetch from the registry API (`curl -s https://registry.hub.docker.com/v2/...` token dance) or — if offline — leave clearly-marked `@sha256:TODO-pin-on-next-build` placeholders and a one-line `docs/RELEASES.md` step describing how to pin; state which path you took. Keep the human-readable tag in a comment above each FROM.
2. **Test whether the build toolchain is needed at all:** lxml 6.x ships manylinux wheels for 3.11, and the remaining deps are pure-Python or wheeled. In a scratch venv: `pip install --only-binary :all: -r requirements.txt` — if it succeeds, delete `gcc g++ libxml2-dev libxslt-dev` from BOTH final stages (keep `tini` in Dockerfile.single). If something genuinely needs compiling, move the toolchain into a wheel-builder stage instead. Record the experiment's result.
3. Remove the obsolete `version: '3.8'` key from `docker-compose.yml`.

## Constraints

- Files in scope: `src/core/egress_manager.py`, `src/core/scraper.py` (impersonate only), requirements files, `pyproject.toml` (deps only), both Dockerfiles, `docker-compose.yml`, `unraid/bind.xml`, docs, tests.
- Do not alter entrypoint supervision or healthchecks (Wave 5-A's work) beyond mechanical adjacency.
- CHANGELOG entries for: impersonation target + config var, dependency bumps, image hardening.

## Verification

```bash
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt   # bumped pins resolve
python -m pytest tests/ -q
ruff check src/ tests/ && mypy src/
docker compose config -q
docker build -f Dockerfile . 2>/dev/null || echo "no docker locally — note for operator to build-verify"
```

## Done criteria

Suite green on bumped deps; impersonation target is current + configurable with fallback; both images create writable data/logs dirs for uid 1001; bases digest-pinned (or TODO-marked with documented procedure); toolchain experiment documented with the resulting Dockerfile state.
