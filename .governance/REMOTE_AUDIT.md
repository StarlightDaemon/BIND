# Remote Audit Protocol: The Forensic Handshake

**Version:** 1.0.0
**Context:** Starlight Carbon Architect auditing a Builder Agent implementation remotely.

## The Problem
The Starlight Carbon Architect (SCA) needs to verify that an external project is 100% compliant with the Design System, but the SCA does **not** have access to that project's filesystem or repository.

## The Solution: Evidence-Zero Audit
We use an "Evidence Bundle" (a machine-readable audit trail) that the implementation agent generates and sends back to the SCA.

---

## 1. The Evidence Bundle
The Builder Agent must run the `audit-collector` script in their workspace to generate a `compliance-evidence.json`. This file contains:

1.  **Dependency Manifest**: Verified list of `@carbon/react` and `@starlight/governance` versions.
2.  **Calculated Token Usage**: A scan of the built CSS/JS to ensure specific hex values match the Starlight source.
3.  **Validator Receipt**: A signed log from the Governance Validator run.
4.  **Structure Digest**: A hash-based overview of the project directory to ensure the Law is embedded correctly.

## 2. Builder Workflow (The Submission)
1.  **Build**: Complete the implementation.
2.  **Generate Evidence**: Run `npm run collect-audit` in the project root.
3.  **Deliver**: Paste the content of `compliance-evidence.json` into the chat for the SCA.

## 3. Architect Workflow (The Verification)
Once the SCA receives the evidence:
1.  **Ingest**: Read the JSON evidence.
2.  **Validate**: Compare the evidence against the local "System of Record" (`.governance/tokens`).
3.  **Certify**:
    - **PASS**: Issue a `Governance Certificate`.
    - **FAIL**: Issue a `Forensics Report` (Drift Analysis) with specific remediation steps.

---

## 4. The Decision Matrix (Auditor Logic)

| Requirement | Evidence Found | Status |
| :--- | :--- | :--- |
| Hardcoded Hex | `#333` found in `app.css` | **FAIL** (Drift Detected) |
| Token Mismatch | `interactive.01` resolves to non-Carbon value | **FAIL** (Corruption) |
| Missing Law | `validator/` missing from scripts | **FAIL** (Anarchy) |
| All Nominal | Manifest matches Law | **PASS** (Certified) |
