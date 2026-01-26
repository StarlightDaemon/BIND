# BIND REPOSITORY HYGIENE — STEP 2
## Cleanup Approval & Scope Lock

**Date:** 2026-01-26
**Governance Authority:** TRON + BIND Canon
**Status:** APPROVED FOR EXECUTION

---

## 1. Approval Summary

Based on the **Step 1: Classification Audit (2026-01-26)**, the following actions are **APPROVED** for immediate execution. The objective is to resolve "root sprawl" and mitigate the "Critical Security Risk" (`credentials.json`) while preserving runtime integrity.

**Authorization Code:** `BIND-HYGIENE-EXEC-001`

---

## 2. Approved Moves

The following items are approved to be **MOVED** to the specified destinations to restore root hierarchy.

| Item Name | Current Location | Approved Destination | Rationale |
| :--- | :--- | :--- | :--- |
| `BIND_AUDIT_REPORT.md` | `/` | `docs/audits/` | Canonical Audit Record |
| `CLU_AUDIT_REPORT.md` | `/` | `docs/audits/` | Canonical Audit Record |
| `COMPLIANCE_REPORT.md` | `/` | `docs/audits/` | Canonical Compliance Record |
| `DRIFT_REPORT.md` | `/` | `docs/audits/` | Canonical Drift Record |
| `UNIFIED_GOVERNANCE_REPORT.md` | `/` | `docs/audits/` | Canonical Governance Record |
| `compliance-evidence.json` | `/` | `docs/audits/evidence/` | Supporting artifact |
| `BIND_UI_AUDIT_REPORT.md` | `/` | `docs/remediation/` | UI Remediation Context |
| `BIND_UI_FINAL_ASSESSMENT.md` | `/` | `docs/remediation/` | UI Remediation Context |
| `BIND_UI_REMEDIATION_REPORT.md` | `/` | `docs/remediation/` | UI Remediation Context |
| `ui-remediation-evidence.json` | `/` | `docs/remediation/evidence/` | Supporting artifact |
| `starlight-governance-kit-v1.0.0/`| `/` | `docs/reference/kits/` | Transitional artifact |
| `magnets/` | `/` | `data/magnets/` | Runtime Data Separation |

> **Note:** Destination directories (`docs/audits/evidence`, `docs/remediation/evidence`, `docs/reference/kits`, `data/magnets`) must be created if they do not exist.

---

## 3. Approved Archives

No items are designated for "Archive" (outside of the repository). All moved items are retained within the `docs/` or `data/` structure for continuity.

---

## 4. Approved Deletions

The following items are approved for **DELETION**.

| Item Name | Classification | Safety Condition |
| :--- | :--- | :--- |
| `credentials.json` | **Critical Security Risk** | **MUST DELETE**. Confirmed untracked. Ensure no production usage. |
| `bind.log` | Runtime Log | Safe to delete. |
| `bind.out` | Runtime Output | Safe to delete. |
| `rss_server.out` | Runtime Output | Safe to delete. |
| `security.log` | Runtime Log | Safe to delete. |
| `server.log` | Runtime Log | Safe to delete. |
| `.coverage` | Test Artifact | Safe to delete. |
| `venv/` | Local Environment | Safe to delete (Recreate if needed). |
| `.pytest_cache/` | Test Cache | Safe to delete. |
| `.ruff_cache/` | Linter Cache | Safe to delete. |

---

## 5. Protected Items

The following items are **STRICTLY PROTECTED** and must NOT be moved, renamed, or deleted.

*   **Core Structure:**
    *   `src/`
    *   `tests/`
    *   `docs/`
    *   `deployment/`
    *   `scripts/`
*   **Root Configs & Metadata:**
    *   `LICENSE`
    *   `README.md`
    *   `CHANGELOG.md`
    *   `.gitignore` (Content update allowed, file deletion prohibited)
    *   `pyproject.toml`
    *   `requirements.txt`
    *   `Dockerfile`
    *   `docker-compose.yml`
    *   `config.env.example`
*   **Deployment Utilities:**
    *   `update.sh` (Retain in root for ease of access)
    *   `.github/`

---

## 6. Follow-Up Required Items

The following actions are required to ensure the cleanup does not break the system:

1.  **`magnets/` Migration:**
    *   Update `config.env` (if exists) or application logic to look for magnets in `data/magnets/` instead of `magnets/`.
    *   Verify `src/bind.py` or `src/rss_server.py` does not hardcode the root path.
2.  **`.gitignore` Update:**
    *   Add `*.log`, `*.out`, `.coverage`, `venv/`, `.pytest_cache/`, `.ruff_cache/`, `data/` (or contents of data) to `.gitignore` to prevent recurrence.
    *   Explicitly ignore `credentials.json`.
3.  **Governance Kit:**
    *   Review `docs/reference/kits/starlight-governance-kit-v1.0.0/` content for integration into `docs/governance/` and delete the kit folder in a future pass.

---

## 7. Execution Readiness Statement

**I certify that:**
1.  All "Move" operations highlight clear destinations.
2.  All "Delete" operations target non-critical, renewable, or dangerous artifacts.
3.  Critical runtime and documentation files are explicitly protected.
4.  Ambiguities (`magnets`, `kit`) have been resolved with preservation strategies (`data/`, `docs/reference/`).

**Hypothesis:** Execution of this plan will result in a clean root directory containing only ~15 essential items, significantly improving project hygiene and security.

**Action:** PROCEED TO EXECUTION.
