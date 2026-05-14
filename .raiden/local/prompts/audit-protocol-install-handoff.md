# Handoff: WORKSPACE_AUDIT_PROTOCOL Edict v0.3.0 Install + Gitignore Remediation + v0.4.0 Update — BIND

## Prompt ID

`raiden.shared.handoff.v1`

## Purpose

Inform the BIND Instance's main agent of changes made by the RAIDEN central agent
across two sessions (2026-05-13 and 2026-05-14):

1. **Phase 1 (2026-05-13):** The WORKSPACE_AUDIT_PROTOCOL Edict v0.3.0 install and the
   `.gitignore` remediation (broad `.raiden/` exclusion replaced with three canonical
   audit-output exclusions, making `.raiden/` and `AGENTS.md` trackable in git).
   A commit is required.

2. **Phase 2 (2026-05-14):** After the Phase 1 commit, the RAIDEN central agent will
   apply the v0.3.0 → v0.4.0 migration update to `WORKSPACE_AUDIT_PROTOCOL.md`.
   A second commit will be required after that.

## Template

```text
You are continuing a bounded work package inside the current repo.

Read first:
- AGENTS.md (on disk; now trackable — was previously gitignored)
- .raiden/README.md
- .raiden/instance/baseline.json
- .raiden/instance/metadata.json
- .raiden/writ/WORKSPACE_AUDIT_PROTOCOL.md
- .gitignore (verify the canonical audit-output exclusion block is present)

Current objective:
- Phase 1: Verify the RAIDEN v0.3.0 install is correct and commit all newly-trackable
  RAIDEN files plus the .gitignore change.
- Phase 2: After Phase 1 commit, the RAIDEN central agent will apply the v0.4.0 update;
  commit the resulting changes when that update arrives.

Known constraints:
- Do NOT modify any file in .raiden/writ/ — RAIDEN already installed the correct content.
- Do NOT modify .gitignore further without operator direction.
- Do NOT run the workspace audit itself.
- Commit attribution: no Co-Authored-By or agent attribution lines in commit messages
  (CLAUDE.md §8 rule 11).

Already true (as of 2026-05-13, RAIDEN central migration sessions):
- WORKSPACE_AUDIT_PROTOCOL.md written to .raiden/writ/ on 2026-05-13.
  SHA-256 (v0.3.0): 2ae05789f2c61c101b9eaf1e9421fc72e9f9565dda22d7c4251aeb5b3baf0261.
  No prior version existed (first install of this Edict in this Instance).
- .raiden/instance/baseline.json updated: WORKSPACE_AUDIT_PROTOCOL.md entry added,
  installed_edict_version 0.2.0 → 0.3.0.
- .raiden/instance/metadata.json updated: installed_edict_version 0.2.0 → 0.3.0.
- .raiden/README.md updated: ## Workspace Audit pointer section added.
- .gitignore updated (2026-05-13, public-instance hardening session):
  - REMOVED: broad .raiden/ exclusion and AGENTS.md exclusion
  - ADDED: three canonical audit-output exclusions under labeled section:
      # RAIDEN audit outputs — operational findings, not framework content
      audit-reports/
      .raiden/state/AUDIT_LOG.md
      .raiden/state/last-audit.md
  - reports/, docs/governance/, docs/NEW_SESSION_HANDOFF.md exclusions preserved

Also true (as of 2026-05-14, v0.4.0 revision):
- The canonical Edict is now at v0.4.0. BIND is at v0.3.0 and needs a v0.4.0 migration
  after the Phase 1 commit completes. The RAIDEN central agent will run
  toolkit/prompts/audit-protocol-migration-v0.4.0-prompt.md targeting BIND after Phase 1.
  The v0.4.0 update changes WORKSPACE_AUDIT_PROTOCOL.md content (five protocol refinements
  — see the v0.4.0 closeout in RAIDEN central for details) and bumps installed_edict_version
  to 0.4.0 in both baseline.json and metadata.json.

Still open — Phase 1:
1. Run verification steps (below) to confirm v0.3.0 install is present and correct.
2. Stage and commit the following files to git:
   - .gitignore (modified)
   - AGENTS.md (newly trackable — was gitignored before)
   - .raiden/ (entire directory — newly trackable; was gitignored before)
   Suggested commit message:
   "chore: install RAIDEN Edict v0.3.0 and enable .raiden/ git tracking"
3. Signal to the operator: Phase 1 commit is done; RAIDEN central can now run the
   v0.4.0 migration prompt targeting /mnt/e/BIND.

Still open — Phase 2 (after RAIDEN central applies v0.4.0):
4. Verify the v0.4.0 update: confirm .raiden/writ/WORKSPACE_AUDIT_PROTOCOL.md hash
   matches 1fa98a0ab068349d71556b142d433fe52462de0cca237d773e4e3dc2ad5bdbb0.
5. Run plan validation (see step 2 of verification steps below, updated for v0.4.0).
6. Commit the v0.4.0 update files:
   - .raiden/writ/WORKSPACE_AUDIT_PROTOCOL.md (updated content)
   - .raiden/instance/baseline.json (hash updated, version 0.3.0 → 0.4.0)
   - .raiden/instance/metadata.json (version 0.3.0 → 0.4.0)
   - .raiden/local/prompts/audit-protocol-install-handoff.md (this file, updated)
   Suggested commit message:
   "chore: update RAIDEN Edict v0.3.0 → v0.4.0 (WORKSPACE_AUDIT_PROTOCOL revision)"

Verification steps (Phase 1):
1. Confirm .raiden/writ/WORKSPACE_AUDIT_PROTOCOL.md exists and is non-empty.
2. Run plan validation from RAIDEN central:
     cd /mnt/e/Raiden/toolkit/updater
     python3 -m raiden_updater.cli plan \
       --instance /mnt/e/BIND \
       --package /mnt/e/Raiden/toolkit/updater/fixtures/sample_package
   NOTE: After Phase 1 only (before v0.4.0 migration), plan will show BIND as
   behind v0.4.0 — this is expected. "Already up to date" only appears after Phase 2.
3. grep installed_edict_version /mnt/e/BIND/.raiden/instance/baseline.json
   → confirms "0.3.0" after Phase 1; "0.4.0" after Phase 2
4. grep installed_edict_version /mnt/e/BIND/.raiden/instance/metadata.json
   → same as above
5. git -C /mnt/e/BIND status --porcelain
   → should show .gitignore modified plus untracked .raiden/ and AGENTS.md
     (confirming .raiden/ is no longer gitignored) before Phase 1 commit
6. Confirm .gitignore contains the three canonical exclusion lines and does NOT contain
   a broad .raiden/ exclusion.

Do not:
- reopen settled naming or architecture
- treat review artifacts as canon unless adopted
- broaden the task beyond the stated objective
- run the workspace audit itself
- modify .gitignore without explicit operator direction

Close out with:
- result: Phase 1 commit made; Phase 2 pending RAIDEN central v0.4.0 migration
- evidence checked: WORKSPACE_AUDIT_PROTOCOL.md presence, plan validator output,
  version grep outputs, git status confirming staged and committed files
- remaining risks: Phase 2 v0.4.0 migration pending; no other risks expected
```
