# BIND — RAIDEN Instance

This repo runs a RAIDEN Instance control plane in `.raiden/`.
See `.raiden/writ/AGENTS.md` for the full agent guide.

## Naming Canon

Use these five terms exactly. No synonyms.

| Term | Meaning |
|---|---|
| RAIDEN | The central framework repo and governing authority |
| Edict | The managed instruction/package that RAIDEN issues |
| RAIDEN Instance | This repo — any downstream repo with a `.raiden/` control plane |
| Writ | The installed managed core in `.raiden/writ/` |
| payload | The installable Edict subset before install; becomes the Writ |

## D-0016 — Four-Point Update Contract

Every Writ update must:
1. Update managed core (`.raiden/writ/`)
2. Preserve local overlay (`.raiden/local/`)
3. Preserve local live state (`.raiden/state/`)
4. Stop and report if any managed file was locally modified — no silent overwrites

## Commit Attribution

Do not add Co-Authored-By or any agent attribution trailer lines.
Commits carry only the operator's git identity.
The commit-msg hook enforces this at the git level. Do not bypass it.

## Write Boundaries

May write: repo source files, `.raiden/local/`, `.raiden/state/`
Must not write: `.raiden/writ/` or the commit-msg hook

## Full Guide

`.raiden/writ/AGENTS.md` — control-plane read order, memory precedence (D-0041),
tooling surface, write boundaries, and Writ contents.
