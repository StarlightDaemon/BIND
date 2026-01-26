# BIND 1.0 — Final Release Decisions

## DEP-01 Decision

**Decision:** ACCEPT AS 1.0 CONSTRAINT

**Rationale:**
The hardcoded `/opt/bind` path is a known characteristic of the current implementation. While it limits deployment flexibility, it aligns with the "Pet" server aspect of the target Proxmox LXC use case. Modifying this behavior would require significant changes to systemd units and helper scripts, introducing regression risk for a change that provides marginal value to the primary user base at this stage.

**Impact on Users:**
Users must install the application in `/opt/bind`. Custom installation paths are not supported in version 1.0.

**Documentation Updates:**
Yes. The installation documentation must explicitly state that `/opt/bind` is the mandatory installation directory.

## LOG-01 Decision

**Decision:** DEFER TO POST-1.0

**Rationale:**
The current behavior of writing logs to the working directory (`/opt/bind/bind.log`) is non-standard for a Linux service but remains functional for debugging and verification. Correcting this to use standard system logging (syslog/journald) or `/var/log` requires code modifications that fall outside the scope of the remaining 1.0 remediation window. This technical debt is substantial enough to warrant a proper fix in a minor release (v1.1) rather than a hasty patch now.

**Impact on Users:**
Logs will be located in `/opt/bind/bind.log`. Standard system log rotation tools may not automatically manage this file unless manually configured. Users should look here for application output instead of `/var/log`.

**Documentation Updates:**
Yes. The troubleshooting and logging sections of the documentation must identify `/opt/bind/bind.log` as the primary log source.

## Summary of Accepted Constraints

The following behaviors are accepted as constraints for the BIND 1.0 release:

*   **Fixed Installation Path:** The application requires installation at `/opt/bind`. Refactoring for path agnosticism is not planned for the 1.0 cycle.
*   **Non-Standard Log Location:** Application logs are written to the application root (`/opt/bind/bind.log`) rather than the standard `/var/log` structure.
