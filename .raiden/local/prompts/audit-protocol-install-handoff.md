You are the BIND Instance agent, operating inside /Users/dante/Citadel/BIND (or the repo root wherever BIND is checked out).

Read first:
- AGENTS.md
- .raiden/README.md
- .raiden/state/CURRENT_STATE.md
- .raiden/writ/WORKSPACE_AUDIT_PROTOCOL.md

Current objective:
Verify and commit the Edict v0.4.0 migration files that RAIDEN central wrote into this Instance on 2026-05-14. No new writes are needed — RAIDEN central completed all file operations; your task is verification and commit only.

Known constraints:
- Do not modify CURRENT_STATE.md, OPEN_LOOPS.md, DECISIONS.md, or WORK_LOG.md.
- Do not push without explicit operator confirmation.
- No Co-Authored-By or agent attribution lines in the commit message.
- Do not run raiden_updater.cli apply — use plan only.

Already true (RAIDEN central wrote these on 2026-05-14):
- .raiden/writ/WORKSPACE_AUDIT_PROTOCOL.md — updated to v0.4.0 content.
  SHA-256: 1fa98a0ab068349d71556b142d433fe52462de0cca237d773e4e3dc2ad5bdbb0
- .raiden/instance/baseline.json — WORKSPACE_AUDIT_PROTOCOL.md hash updated
  (2ae05789... → 1fa98a0a...); installed_edict_version bumped 0.3.0 → 0.4.0.
- .raiden/instance/metadata.json — installed_edict_version bumped 0.3.0 → 0.4.0.
- .raiden/README.md — ## Workspace Audit section already present from v0.3.0; no change.
- .gitignore — audit-output exclusion block already present; no change.
- This file (.raiden/local/prompts/audit-protocol-install-handoff.md) — updated by RAIDEN central.

Still open:
1. Run `git status --porcelain` — confirm only the migration files below appear as modified
   or untracked. Any unexpected files: stop and surface to operator before proceeding.
2. Run `grep installed_edict_version .raiden/instance/metadata.json`
   → expected: "0.4.0"
3. Run from /Users/dante/Citadel/Raiden/toolkit/updater/ (RAIDEN central):
     python3 -m raiden_updater.cli plan \
       --instance /Users/dante/Citadel/BIND \
       --package /Users/dante/Citadel/Raiden/toolkit/updater/fixtures/sample_package
   → expected: Block reason: Already up to date — no changes needed
   If any other result: stop and surface to operator.
4. Stage and commit the following files:
     .raiden/writ/WORKSPACE_AUDIT_PROTOCOL.md
     .raiden/instance/baseline.json
     .raiden/instance/metadata.json
     .raiden/local/prompts/audit-protocol-install-handoff.md
   Note: .raiden/README.md and .gitignore were NOT modified this session — do not include.
   Suggested commit message:
     "install: RAIDEN Edict v0.3.0 → v0.4.0 (WORKSPACE_AUDIT_PROTOCOL revision)"
5. Run `git status --porcelain` after commit — confirm clean.

Do not:
- Modify any managed file in .raiden/writ/
- Reopen settled naming or architecture
- Treat review artifacts as canon unless adopted
- Broaden the task beyond committing the files listed above
- Run the workspace audit itself

Close out with:
- result: commit SHA
- evidence checked: git diff output, plan validator output, version grep result
- remaining risks: none expected; surface any anomaly observed
