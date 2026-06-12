# BIND Coverage Operator Guide

**Start:** 76.54% &nbsp;·&nbsp; **Achieved:** 97.50% (397 tests) &nbsp;·&nbsp; **Goal:** 85%+ ✅

Check coverage at any time:
```bash
python -m pytest tests/ --cov=src --cov-report=term-missing -q
```

---

## Wave 1 — COMPLETE ✅

All six prompts ran. Coverage jumped from 76.54% → 97.50%, far exceeding the 85% target.

| | Prompt | Model | Est. gain | Status |
|---|---|---|---|---|
| A | [wave1-a-rss-authenticated-routes.md](wave1-a-rss-authenticated-routes.md) | 🔵 Claude Sonnet | +5.5% | ✅ Done |
| C | [wave1-c-bind-daemon.md](wave1-c-bind-daemon.md) | 🔵 Claude Sonnet | +2.5% | ✅ Done |
| D | [wave1-d-scraper-network.md](wave1-d-scraper-network.md) | 🔵 Claude Sonnet | +2.0% | ✅ Done |
| F-core | [wave1-f-core.md](wave1-f-core.md) | 🔵 Claude Sonnet | +0.8% | ✅ Done |
| F-flask | [wave1-f-flask.md](wave1-f-flask.md) | 🔵 Claude Sonnet | +0.8% | ✅ Done |
| G | [wave1-g-easy-wins.md](wave1-g-easy-wins.md) | 🔵 Claude Sonnet | +0.8% | ✅ Done |

---

## Wave 2 — COMPLETE ✅ (verified 2026-06-12)

Verification agents confirmed all Wave 2 targets were already covered by tests
present in the tree (uncommitted leftovers from earlier runs, landed in commit
e431099). No new tests were needed. Suite: 455 passed, 97.18% coverage.

| | Prompt | Model | Est. gain | Status |
|---|---|---|---|---|
| B | [wave2-b-rss-csrf-setup.md](wave2-b-rss-csrf-setup.md) | 🔵 Claude Sonnet | +1.5% | ✅ Already covered |
| E | [wave2-e-scraper-parse-strategies.md](wave2-e-scraper-parse-strategies.md) | 🔵 Claude Sonnet | +1.2% | ✅ Already covered |

---

## Flow at a glance

```
Wave 1 (complete)             Wave 2 (ready)
─────────────────────         ────────────────────────
A ──────────────────────────► B  (prereq: A ✅)
C
D ──────────────────────────► E  (prereq: D ✅)
F-core
F-flask
G
```

---

## Model key

> **2026-06-12:** This prompt set runs exclusively on native Claude models. Every
> prompt's model column shows the Claude model to use if it is run (or re-run) today.
> The pending wave2-e prompt was reformatted as a Claude prompt (working directory
> also corrected from the old WSL path).

| | Model | Best for |
|---|---|---|
| 🔵 | Claude Sonnet | Well-specified test/code work: route patterns, fixtures, pure functions, session mechanics, complex mocks |
| | Claude Opus | Security semantics, concurrency, process lifecycle, exception hierarchies, analysis judgment |
| | Claude Fable | Cross-component daemon↔RSS changes with rolling-upgrade sequencing |

---

# Remediation Prompt Set (Waves 4–6)

Remediates the findings in [`BIND_FULL_AUDIT_REPORT.md`](../../BIND_FULL_AUDIT_REPORT.md) (repo root).
14 work packages grouped by **code surface** (not by model), so each session produces one
reviewable, independently verifiable diff with its own regression tests.
Prompts cite line numbers from audit time and instruct agents to locate by symbol if drifted.

## Wave 4 — Independent fixes (run in any order, one at a time per shared file)

| | Prompt | Model | Findings | Constraint |
|---|---|---|---|---|
| A | [wave4-a-security-mechanics.md](wave4-a-security-mechanics.md) | 🔵 Claude Sonnet | SEC-1, SEC-4, SEC-5, CQ-3, TEST-1 | Run **first** in Wave 4 |
| B | [wave4-b-xff-trusted-proxies.md](wave4-b-xff-trusted-proxies.md) | Claude Opus | SEC-3 | Not concurrent with C (both edit security.py) |
| C | [wave4-c-session-credential-hardening.md](wave4-c-session-credential-hardening.md) | Claude Opus | SEC-6, SEC-7, SEC-8, SEC-9, TEST-2 | Not concurrent with B |
| D | [wave4-d-retry-classification.md](wave4-d-retry-classification.md) | Claude Opus | RES-2 | Fully independent |
| E | [wave4-e-config-storage-mechanics.md](wave4-e-config-storage-mechanics.md) | 🔵 Claude Sonnet | ARCH-4, RES-1, RES-5, TEST-4 | **Must commit before 5-B** |

## Wave 5 — Architecture (strict order: A → B → C; never concurrent — all edit bind.py)

| | Prompt | Model | Findings | Prereq |
|---|---|---|---|---|
| A | [wave5-a-daemon-heartbeat-healthchecks.md](wave5-a-daemon-heartbeat-healthchecks.md) | **Claude Fable** | ARCH-1, DEP-2, DEP-6, ARCH-6 | — |
| B | [wave5-b-scraping-control-plane.md](wave5-b-scraping-control-plane.md) | **Claude Fable** | ARCH-2, ARCH-3, SEC-2 | 4-E committed |
| C | [wave5-c-daemon-lifecycle-concurrency.md](wave5-c-daemon-lifecycle-concurrency.md) | Claude Opus | RES-4, ARCH-5 | 5-B committed |

## Wave 6 — Follow-ups

| | Prompt | Model | Findings | Prereq |
|---|---|---|---|---|
| A | [wave6-a-integration-tests.md](wave6-a-integration-tests.md) | Claude Opus | TEST-3 | 5-A + 5-B committed |
| B | [wave6-b-type-safety.md](wave6-b-type-safety.md) | Claude Opus | CQ-1 | Waves 4 + 5 committed |
| C | [wave6-c-cloudscraper-analysis.md](wave6-c-cloudscraper-analysis.md) | Claude Opus | DEP-D1 (analysis only) | — (anytime) |
| D | [wave6-d-deps-image-hygiene.md](wave6-d-deps-image-hygiene.md) | 🔵 Claude Sonnet | DEP-D2, DEP-D3, DEP-3, DEP-5 | 5-A committed |
| E | [wave6-e-frontend-error-surface.md](wave6-e-frontend-error-surface.md) | 🔵 Claude Sonnet | FE-2, FE-4 | After 4-A/4-C/5-B if in flight |
| F | [wave6-f-dead-code-version-skew.md](wave6-f-dead-code-version-skew.md) | 🔵 Claude Sonnet | CQ-4, version skew, RES-3 | 4-A committed; run **LAST** |

## Flow at a glance

```
Wave 4                          Wave 5                    Wave 6
──────────────────────          ──────────────────        ─────────────────────────
A (first) ──────────────────────────────────────────────► F (last)
B ─┐ (not concurrent)
C ─┘
D
E ─────────────────────────────► B ──► C ──────────────► A (integration tests)
                          A ──┘   └────────────────────► A
                          A ────────────────────────────► D
                                  4+5 all committed ────► B (type safety)
C (analysis) — anytime            E — anytime (sequence around rss_server edits)
```

Maximum safe parallelism: **4-A + 4-D + 6-C** can run simultaneously on day one;
then 4-B/4-C (serially) + 4-E; then Wave 5 strictly serial; Wave 6 fans out.

## Model key (remediation)

| Model | Used for |
|---|---|
| **Claude Fable** | Cross-component daemon↔RSS changes with rolling-upgrade sequencing (5-A, 5-B) |
| Claude Opus | Security semantics, concurrency, process lifecycle, exception hierarchies, analysis judgment |
| 🔵 Claude Sonnet | Well-specified mechanical fixes — the audit report carries the full spec |

## Operator checklist per prompt

1. Confirm the prereq column — prereqs mean **committed to main**, not merely run.
2. Launch the prompt verbatim in a fresh session of the listed model.
3. Gate every merge on: `pytest -q` green, `ruff check`, `mypy src/`, and (where touched) `npx tsc --noEmit`.
4. Each prompt accumulates CHANGELOG entries under `## [Unreleased]`; Wave 6-F folds them into a release.

## Execution modes

Two verified ways to run this program:

- **Operator-launched sessions** (default): one fresh session of the listed model per prompt, operator enforces the prereq/sequencing rules above.
- **In-session delegation** (verified 2026-06-12): a Claude Fable session dispatches each prompt to a subagent with the matching model override (`sonnet` / `opus` / `haiku` all confirmed routable via self-identification test). Fable enforces sequencing, runs the merge-gate verification itself after each subagent returns (subagent self-reports are leads, not facts), handles the Fable-tier prompts directly, and falls back to doing a prompt itself if a subagent stalls or fails its gate twice. Throttle: ≤3 concurrent subagents, only on disjoint file sets; usage windows checked between waves.
