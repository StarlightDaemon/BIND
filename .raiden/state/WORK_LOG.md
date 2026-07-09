# Work Log

## 2026-07-09 — Edict v2.0.0 + state normalization

- Edict updated 1.0.1 → 2.0.0 via `raiden_updater.cli plan`/`apply`:
  AGENTS.md, FORK_REVIEW_PROTOCOL.md, OPERATING_RULES.md, README.md,
  WORKSPACE_AUDIT_PROTOCOL.md updated in `.raiden/writ/`; ROUTING_POLICY.md
  added; MODEL_TIERS.md removed (`managed_file_removal` warning, expected —
  the routing policy replaces the retired capability-tier scheme). Hook
  `commit-msg` unchanged. Re-plan confirmed "Already up to date."
- `.raiden/instance/metadata.json` stamped `state_schema_version: 2`.
- Routing overlay replaced: `.raiden/local/MODEL_MAP.md` removed (`git rm`),
  `.raiden/local/ROUTING.md` added — operator-local ladder mapping for the
  new `ROUTING_POLICY.md` Edict.
- Root `CLAUDE.md` folded in per the new CLAUDE.md-pointer rule
  (`OPERATING_RULES.md` "Root CLAUDE.md Is a Pointer Only"): its prior
  substantive content (agent-prompt-file conventions, model-naming table,
  Gemini prompt fencing convention, coverage-work conventions) moved
  verbatim to `.raiden/local/rules/legacy-claude-guidance.md`; root
  `CLAUDE.md` reduced to a 3-line pointer to `AGENTS.md`.
- State normalization pass (Fact-Home Rule, `OPERATING_RULES.md`): removed
  the hand-written "Last Updated: 2026-07-08" footer from CURRENT_STATE.md
  (freshness is now derived from git history, per the rule). Removed the
  "## Edict Version" section and the "Edict upgraded from v0.6.1 to v1.0.0"
  Recent-Work bullet from CURRENT_STATE.md — the installed Edict version is
  authoritative only in `metadata.json` and must never be restated in state
  prose. Relocating rather than deleting that history: CURRENT_STATE.md
  previously recorded that the Edict was upgraded from v0.6.1 to v1.0.0 on
  2026-06-14 (subsequently to v1.0.1 per commit 64e6117, and now to v2.0.0
  as of this entry). Also collapsed CURRENT_STATE.md's "Open Loops" and
  "Deferred" sections, which restated per-loop open/closed status, into a
  single bare-ID citation of OPEN_LOOPS.md.

## 2026-05-15 — RAIDEN state population

- State files populated (CURRENT_STATE.md, GOALS.md, DECISIONS.md, OPEN_LOOPS.md, WORK_LOG.md) to reflect v1.7.1 reality.
- OL-1 and OL-2 marked closed; both were resolved in v1.7.0 (shipped after the 2026-05-12 audit that opened them).
- Session-startup prompt seeded to `.raiden/local/prompts/` (D-0039 one-off seed).

## 2026-05-13 — RAIDEN Edict v0.3.0 → v0.4.0 migration

- WORKSPACE_AUDIT_PROTOCOL.md installed in Writ; baseline and metadata updated; gitignore remediation committed.

## 2026-05-12 — Architecture audit + v1.7.0 SQLite migration

- Architecture audit: R1–R10 implemented; R11 resolved as part of v1.7.0.
- v1.7.0: flat-file storage replaced by SQLite MagnetStore; retention cap and MAX_ITEMS removed; 193 tests pass.
- v1.7.1: Docker Hub CI, secret key auto-gen, cloudscraper proxy, settings UI.
