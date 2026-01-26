# BIND REPOSITORY HYGIENE — STEP 1
## Root Workspace Planning & Classification Audit

**Date:** 2026-01-26
**Scope:** Repository ROOT ONLY
**Status:** DRAFT (Read-Only Analysis)

---

## 1. Executive Summary

The BIND repository root adheres partially to standard Python/Docker project structures but suffers from significant "root sprawl." 42 items were examined. While core runtime and deployment artifacts are present, the root directory is heavily polluted with operational logs, temporary reports, misplaced governance artifacts, and at least one critical security risk (`credentials.json`).

The structure suggests organic growth where runtime, governance, documentation, and operational data are co-mingled. Immediate hygiene actions are required to separate these concerns, specifically moving logs, reports, and transitional artifacts to appropriate subdirectories or ignoring them.

---

## 2. Root Workspace Inventory

**Total Items:** 42 (28 Files, 14 Directories)

### Directories
- `.git/`
- `.github/`
- `.governance/`
- `.pytest_cache/`
- `.ruff_cache/`
- `.vscode/`
- `deployment/`
- `docs/`
- `magnets/`
- `scripts/`
- `src/`
- `starlight-governance-kit-v1.0.0/`
- `tests/`
- `venv/`

### Files
- `.coverage`
- `.gitignore`
- `.mailmap`
- `BIND_AUDIT_REPORT.md`
- `BIND_UI_AUDIT_REPORT.md`
- `BIND_UI_FINAL_ASSESSMENT.md`
- `BIND_UI_REMEDIATION_REPORT.md`
- `CHANGELOG.md`
- `CLU_AUDIT_REPORT.md`
- `COMPLIANCE_REPORT.md`
- `DRIFT_REPORT.md`
- `Dockerfile`
- `LICENSE`
- `README.md`
- `UNIFIED_GOVERNANCE_REPORT.md`
- `bind.log`
- `bind.out`
- `compliance-evidence.json`
- `config.env.example`
- `credentials.json`
- `docker-compose.yml`
- `pyproject.toml`
- `requirements.txt`
- `rss_server.out`
- `security.log`
- `server.log`
- `ui-remediation-evidence.json`
- `update.sh`

---

## 3. Artifact Classification Table

| Name | Type | Classification | Reasoning |
| :--- | :--- | :--- | :--- |
| `.gitignore` | File | **A. Canonical Runtime** | Repository configuration required for development/packaging. |
| `config.env.example` | File | **A. Canonical Runtime** | Template configuration required for runtime setup. |
| `pyproject.toml` | File | **A. Canonical Runtime** | Python packaging and build configuration. |
| `requirements.txt` | File | **A. Canonical Runtime** | Python dependency manifest. |
| `src/` | Dir | **A. Canonical Runtime** | Core application source code. |
| `tests/` | Dir | **A. Canonical Runtime** | Standard location for source-coupled tests (arguably D, but standard root fixture). |
| `.mailmap` | File | **B. Canonical Governance** | Git authorship standardization. |
| `CHANGELOG.md` | File | **B. Canonical Governance** | Project history documentation. |
| `LICENSE` | File | **B. Canonical Governance** | Legal framework. |
| `README.md` | File | **B. Canonical Governance** | Entry point documentation. |
| `.governance/` | Dir | **B. Canonical Governance** | Hidden governance definitions/standards. |
| `Dockerfile` | File | **C. Canonical Deployment** | Container definition. |
| `docker-compose.yml` | File | **C. Canonical Deployment** | Orchestration config. |
| `deployment/` | Dir | **C. Canonical Deployment** | Deployment scripts/resources. |
| `update.sh` | File | **C. Canonical Deployment** | Operational update utility. |
| `.github/` | Dir | **C. Canonical Deployment** | CI/CD workflows (GitHub Actions). |
| `.vscode/` | Dir | **D. Scripts / Tooling** | IDE configuration (Editor settings). |
| `scripts/` | Dir | **D. Scripts / Tooling** | Helper scripts directory. |
| `.coverage` | File | **D. Scripts / Tooling** | Test coverage footprint (should likely be ignored). |
| `.pytest_cache/` | Dir | **D. Scripts / Tooling** | Test cache (should likely be ignored). |
| `.ruff_cache/` | Dir | **D. Scripts / Tooling** | Linter cache (should likely be ignored). |
| `BIND_AUDIT_REPORT.md` | File | **E. Transitional** | Point-in-time audit artifact. |
| `BIND_UI_AUDIT_REPORT.md` | File | **E. Transitional** | Point-in-time audit artifact. |
| `BIND_UI_FINAL_ASSESSMENT.md`| File | **E. Transitional** | Point-in-time assessment. |
| `BIND_UI_REMEDIATION_REPORT.md`| File | **E. Transitional** | Remediation record. |
| `CLU_AUDIT_REPORT.md` | File | **E. Transitional** | Operational audit record. |
| `COMPLIANCE_REPORT.md` | File | **E. Transitional** | Compliance snapshot. |
| `DRIFT_REPORT.md` | File | **E. Transitional** | State drift snapshot. |
| `UNIFIED_GOVERNANCE_REPORT.md`| File | **E. Transitional** | Unified reporting snapshot. |
| `compliance-evidence.json` | File | **E. Transitional** | Supporting data for compliance report. |
| `ui-remediation-evidence.json`| File | **E. Transitional** | Supporting data for UI remediation. |
| `starlight-governance-kit-v1.0.0/`| Dir | **E. Transitional** | Unpacked release artifact/kit. |
| `credentials.json` | File | **F. Accidental / Obsolete** | **CRITICAL RISK**. Live credentials file. |
| `bind.log` | File | **F. Accidental / Obsolete** | Runtime log file. |
| `bind.out` | File | **F. Accidental / Obsolete** | Speculated standard output capture. |
| `rss_server.out` | File | **F. Accidental / Obsolete** | Speculated standard output capture. |
| `security.log` | File | **F. Accidental / Obsolete** | Runtime security log. |
| `server.log` | File | **F. Accidental / Obsolete** | Runtime server log. |
| `venv/` | Dir | **F. Accidental / Obsolete** | Local environment (should be ignored). |
| `magnets/` | Dir | **G. Unclear** | Runtime data directory (magnets). Should not be in root. |

---

## 4. Structural Findings

1.  **High Noise Ratio**: The root directory is 50%+ occupied by files that are not required for the project structure (logs, reports, evidence, transitional kits).
2.  **Mixed Concerns**:
    - **Runtime vs. Data**: `magnets/` and `*.log` files indicate the application is writing data to the source root at runtime.
    - **Source vs. Ops**: `update.sh` and `deployment/` coexist with `Overview` docs.
3.  **Governance Sprawl**: A significant number of `*_REPORT.md` files clutter the root, likely from recent audit activities. These obscure the `README.md` and `CHANGELOG.md`.

---

## 5. Risk & Ambiguity Analysis

### Critical Risks
-   **`credentials.json`**: This file contains a hashed password and username `admintest`. While potentially a test credential, its presence in the root (and potentially git) is a violation of security practices. It should be `.gitignore`d or moved to a private config path.

### Ambiguities
-   **`magnets/`**: Contains runtime text files (`magnets_*.txt`). This appears to be application state/data. It is classified as **G (Unclear)** but effectively functions as **Runtime Data**. Recommendation is to treat it as data storage that should be configured significantly deeper in the directory tree (e.g., `data/magnets`) or ignored.
-   **`starlight-governance-kit-v1.0.0/`**: Appears to be an unpacked external resource. It should likely be moved to `docs/reference` or deleted if its contents have been integrated.

---

## 6. Recommended Next Actions (No execution)

> “These are recommendations only. No actions taken.”

### IMMEDIATE ACTION (SECURITY)
-   [ ] **credentials.json**: Add to `.gitignore`. Move existing file to a secure location or delete if test-only.

### CLEANUP
1.  **Move Reports**: Create `docs/audits/` or `docs/governance/` and move all `*_REPORT.md` and `*-evidence.json` files there.
2.  **Archive Kit**: Move `starlight-governance-kit-v1.0.0/` to `docs/reference/` or `archives/` if needed, otherwise delete.
3.  **Ignore Runtime Artifacts**: Add `*.log`, `*.out`, `.coverage`, `.pytest_cache`, `.ruff_cache`, `venv/` to `.gitignore`.
4.  **Relocate Data**: Define a clear data directory (e.g., `data/`) for `magnets/` and update application config (`config.env` references) to point there.

### REORGANIZE
-   **Structure**: The remaining files (`src`, `tests`, `docs`, `deployment`, `scripts`) form a solid canonical base. Once the noise is removed, the root will be clean.

---

## 7. Appendix
-   **Note on `tests/`**: Classified as **A (Canonical Runtime)** for this audit as it is standard structure, though strictly it falls under Tooling/QA.
-   **Note on `update.sh`**: Classified as **C (Deployment)**. It duplicates logic often found in `scripts/` but is acceptable in root for ease of access if documented.
