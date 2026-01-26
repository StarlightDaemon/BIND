# BIND 1.0 — Remediation Ledger

**Date:** 2026-01-26
**Source:** BIND — Strategic Full-Scope Readiness Audit
**Status:** Planning

---

## 1. Governance & Scope

This ledger tracks the specific technical debts and defects that must be resolved to declare BIND "1.0 Ready".
* **Canonical Only:** Remediation focuses strictly on aligning the system with its documented intent.
* **No New Features:** Only stability, correctness, and safety fixes are permitted.

---

## 2. Issue Ledger

### [CONF-01] Configuration Pipeline Broken

*   **Description:** The `bind.service` unit does not load the `config.env` file. Changes made via the Web UI are written to disk but ignored by the Daemon process, which continues using defaults or hardcoded values.
*   **Impact on 1.0 Readiness:** **Critical**. The "Settings" feature in the UI is functionally broken for the backend, undermining the primary user interface for configuration.
*   **Dependencies:** None.
*   **Verification Criteria:**
    1.  A value (e.g., `SCRAPE_INTERVAL` or `ABB_URL`) is modified in the Web UI.
    2.  The `config.env` file on disk reflects this change.
    3.  After the automatic (or manual) restart, the Daemon process logs show initialization with the new value.

### [DOC-01] Security Documentation Drift

*   **Description:** The `README.md` and other documentation explicitly state "BIND has no authentication" and recommend external proxies. In reality, the codebase implements a robust authentication system (Setup Wizard, hashed passwords, session management, lockout).
*   **Impact on 1.0 Readiness:** **Major**. Discrepancy creates confusion about the system's security posture and may lead users to implement unnecessary or conflicting partial protections.
*   **Dependencies:** None.
*   **Verification Criteria:**
    1.  `README.md` accurately describes the built-in authentication features.
    2.  Security guidance aligns with the actual code capabilities (Setup Wizard, Brute-force protection).

### [OPS-01] Restart Logic Flaw

*   **Description:** The `ConfigManager.restart_daemon` capability attempts to restart the service to apply settings. Due to **CONF-01**, this restart is performative only; the new settings are not ingested by the restarted process.
*   **Impact on 1.0 Readiness:** **Major**. Users are given false positive feedback that their settings have been applied.
*   **Dependencies:** **CONF-01** (Fixing the pipeline will likely resolve this, but it requires independent verification).
*   **Verification Criteria:**
    1.  The "Save & Restart" action in the UI results in the Daemon process effectively reloading its configuration.

### [DEP-01] Hardcoded Service Paths

*   **Description:** Systemd service units (`bind.service`, `bind-rss.service`) and helper scripts hardcode the installation path to `/opt/bind`.
*   **Impact on 1.0 Readiness:** **Minor**. Limits deployment flexibility and adheres to a "Pet" server model, though acceptable for the specific Proxmox use case.
*   **Dependencies:** None.
*   **Verification Criteria:**
    1.  Documentation acknowledges the `/opt/bind` requirement strictly OR the service units are updated to be path-agnostic. (Decision required during execution).

### [LOG-01] Log File Location

*   **Description:** The Daemon writes `bind.log` to its current working directory (defined as `/opt/bind` in service files) rather than a standard log directory like `/var/log`.
*   **Impact on 1.0 Readiness:** **Minor**. Non-standard behavior for a Linux service, potentially complicating log rotation and monitoring.
*   **Dependencies:** None.
*   **Verification Criteria:**
    1.  Logs are reliably accessible via `journalctl` (standard output) OR written to a well-defined, configurable file location.

---
**End of Ledger**
