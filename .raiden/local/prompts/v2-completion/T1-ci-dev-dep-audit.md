# T1 — CI Dev Dependency Audit

## Prompt ID

`bind.v2.T1.ci-dev-dep-audit.v1`

## Purpose

Add `pip-audit` coverage for dev dependencies in CI. Currently only production
deps are audited; a pytest CVE was caught by manual audit, not CI.

## Agent Type

**Claude Code** — single-file CI change with one verification step.

## Model

**Primary:** `claude-haiku-4-5-20251001`
Rationale: Fully mechanical. One new YAML step plus a requirements-dev.txt
check. No reasoning depth required — Haiku executes this faster and cheaper
than any larger model with identical output quality.

**Secondary:** `claude-sonnet-4-6`
Use if Haiku produces malformed YAML or misidentifies which packages belong
in requirements-dev.txt.

## Phase

Phase 1 — runs **in parallel** with T2 and T3. No dependencies on other tasks.

---

## Prompt

You are working in the repository at `/mnt/e/BIND`.

BIND is a Python audiobook metadata daemon (v1.7.1). This task is a small CI
hardening change with no Python source modifications.

### Problem

`.github/workflows/ci.yml` audits production dependencies with:

```yaml
- name: Audit dependencies for vulnerabilities
  run: |
    pip install pip-audit
    pip-audit -r requirements.txt
```

Dev dependencies (`requirements-dev.txt`) are never audited. A high-severity
CVE in pytest (CVE-2025-71176) was caught by a manual audit rather than CI,
exposing this gap.

### Task

**Step 1 — Verify `requirements-dev.txt` is complete.**

Open `requirements-dev.txt` at the repo root. Confirm it contains at minimum:
`pytest`, `pytest-cov`, `pytest-mock`, `mypy`, and `ruff`. Cross-reference
against `pyproject.toml` `[project.optional-dependencies] dev`. If any package
present in pyproject.toml dev deps is missing from requirements-dev.txt, add it
pinned to the version already in use (check `.venv/lib/.../dist-info/` if
needed). Do not add packages that are not already in use.

**Step 2 — Add the audit step to CI.**

In `.github/workflows/ci.yml`, immediately after the existing
"Audit dependencies for vulnerabilities" step, insert:

```yaml
      - name: Audit dev dependencies for vulnerabilities
        run: pip-audit -r requirements-dev.txt
```

Preserve existing indentation (2-space YAML indent under `steps:`).

**Step 3 — Local verification.**

Run `pip-audit -r requirements-dev.txt` from the repo root to confirm it
executes cleanly. If a vulnerability is found, report it as a finding — do
not suppress it.

### Exit Criteria

- `.github/workflows/ci.yml` contains two pip-audit steps: one for
  `requirements.txt`, one for `requirements-dev.txt`
- `requirements-dev.txt` contains all dev packages already in use
- `pip-audit -r requirements-dev.txt` runs without error locally
- No Python source files were modified
