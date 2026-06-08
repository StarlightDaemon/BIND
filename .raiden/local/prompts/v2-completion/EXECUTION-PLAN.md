# BIND v2 Completion — Execution Plan

**Prepared:** 2026-06-04  
**Scope:** Five remaining work items to close out the BIND v2 roadmap and reach
long-term stable status.

---

## Quick Reference

| ID | Task | Model (Primary) | Model (Secondary) | Phase | Prompt |
|----|------|-----------------|--------------------|-------|--------|
| T1 | CI dev dep audit | `claude-haiku-4-5-20251001` | `claude-sonnet-4-6` | 1 — parallel | [T1-ci-dev-dep-audit.md](T1-ci-dev-dep-audit.md) |
| T2 | Domain resilience probe | `claude-sonnet-4-6` | `claude-opus-4-8` | 1 — parallel | [T2-domain-resilience.md](T2-domain-resilience.md) |
| T3 | Metrics dashboard | `claude-sonnet-4-6` | `claude-opus-4-8` | 1 — parallel | [T3-metrics-dashboard.md](T3-metrics-dashboard.md) |
| T4 | Coverage threshold + tests | `claude-sonnet-4-6` | `claude-opus-4-8` | 2 — after Phase 1 | [T4-coverage-threshold.md](T4-coverage-threshold.md) |
| T5 | Codecov integration | `claude-haiku-4-5-20251001` | `claude-sonnet-4-6` | 3 — human-gated | [T5-codecov.md](T5-codecov.md) |

---

## Dependency Graph

```
Phase 1 (run in parallel):
  T1 ──────────────────────┐
  T2 ──────────────────────┼──► merge all three, CI green
  T3 ──────────────────────┘           │
                                        │
Phase 2 (sequential):                   ▼
                                T4 ─────────────► merge, CI green
                                                        │
Phase 3 (human-gated):                                  ▼
                              [create Codecov account]
                                        │
                                        ▼
                                       T5
```

---

## Phase 1 — Parallel (Run Together)

All three tasks are independent. They touch non-overlapping files with one
minor exception: T2 modifies the `/health` route in `rss_server.py` and T3
adds a new `/metrics` route to the same file. These are different line ranges
and will not conflict.

**If using parallel worktrees or separate branches:** Launch all three agents
simultaneously. Review and merge in any order.

**If running sequentially** (single branch, one agent at a time): Run in the
order T1 → T2 → T3. Each commit stands alone and CI should pass after each.

---

### T1 — CI Dev Dependency Audit

**Prompt file:** [T1-ci-dev-dep-audit.md](T1-ci-dev-dep-audit.md)

**Model:** `claude-haiku-4-5-20251001`

**What it does:** Adds a `pip-audit -r requirements-dev.txt` step to CI so dev
dependency CVEs (like the pytest one caught manually) are caught automatically
on every push.

**How to run:**
- Open a Claude Code session at `/Users/dante/Citadel/BIND`
- Paste the contents of the **Prompt** section from the file above
- Expected duration: ~10 minutes
- Expected output: 1 CI file modified, possibly requirements-dev.txt updated

**Verify before moving on:**
```bash
git diff .github/workflows/ci.yml   # should show new audit step
pip-audit -r requirements-dev.txt   # should run clean
```

---

### T2 — Domain Change Resilience Probe

**Prompt file:** [T2-domain-resilience.md](T2-domain-resilience.md)

**Model:** `claude-sonnet-4-6`

**What it does:** Adds `BindScraper.probe_target()` that classifies target
domain health into four states. Surfaces the result in `/health` (cached 5 min)
and logs a startup WARNING when the domain is unreachable or serving wrong
content.

**How to run:**
- Open a Claude Code session at `/Users/dante/Citadel/BIND`
- Paste the contents of the **Prompt** section from the file above
- Expected duration: 45–90 minutes
- Files touched: `src/core/scraper.py`, `src/bind.py`, `src/rss_server.py`,
  new `tests/test_scraper_probe.py`

**Verify before moving on:**
```bash
pytest tests/test_scraper_probe.py -v   # 4+ tests pass
mypy src/
ruff check src/ tests/
```

---

### T3 — Metrics Dashboard

**Prompt file:** [T3-metrics-dashboard.md](T3-metrics-dashboard.md)

**Model:** `claude-sonnet-4-6`

**What it does:** Extends `MagnetStore.stats()` with 7/30-day counts, adds a
`scrape_runs` table with `record_scrape_run()`, instruments `bind.py` to record
each cycle, and adds an auth-gated `/metrics` HTML page in the Vesper theme.

**How to run:**
- Open a Claude Code session at `/Users/dante/Citadel/BIND`
- Paste the contents of the **Prompt** section from the file above
- Expected duration: 2–3 hours
- Files touched: `src/core/storage.py`, `src/rss_server.py`, `src/bind.py`,
  new `src/templates/metrics.html`, new `tests/test_metrics.py`

**Verify before moving on:**
```bash
pytest tests/test_metrics.py -v
pytest --tb=short                  # full suite, no regressions
mypy src/
# Start the dev server and visit /metrics in browser to confirm layout
```

---

## Phase 2 — Sequential (After Phase 1 Merged)

**Gate:** All of T1, T2, T3 must be merged and CI must be green before starting.

---

### T4 — Coverage Threshold + Storage Tests

**Prompt file:** [T4-coverage-threshold.md](T4-coverage-threshold.md)

**Model:** `claude-sonnet-4-6`

**What it does:** Runs a coverage baseline, writes real-SQLite tests for
`MagnetStore` (≥12 cases), fills remaining gaps in other modules, then raises
`--cov-fail-under` from 40 to 75 in both `pyproject.toml` and CI.

**How to run:**
- Confirm Phase 1 is merged: `git log --oneline -5`
- Confirm CI is green on main before starting
- Open a Claude Code session at `/Users/dante/Citadel/BIND`
- Paste the contents of the **Prompt** section from the file above
- Expected duration: 2–3 hours

**Verify before moving on:**
```bash
pytest --cov=src --cov-report=term-missing --cov-fail-under=75
```
This must exit 0. If it exits non-zero the task is not complete.

---

## Phase 3 — Human-Gated

**Gate:** Human must complete 4 manual steps before handing off to the agent.

---

### T5 — Codecov Integration

**Prompt file:** [T5-codecov.md](T5-codecov.md)

**Model:** `claude-haiku-4-5-20251001`

**Human prerequisites (do these yourself first):**
1. Create account at `https://codecov.io`
2. Link repository `StarlightDaemon/BIND` (GitHub OAuth)
3. Copy the **upload token** from the Codecov repo settings page
4. Add it as a secret in GitHub: repo Settings → Secrets and variables →
   Actions → New secret → name: `CODECOV_TOKEN`
5. Copy the **graph token** (read-only, shown separately on the Codecov
   dashboard) — you will give this to the agent

**How to run the agent:**
- Open a Claude Code session at `/Users/dante/Citadel/BIND`
- Paste the **Prompt** section from the file above
- Supply the graph token when instructed in the prompt (replace
  `CODECOV_GRAPH_TOKEN` placeholder)
- Expected duration: ~10 minutes

---

## Model Selection Rationale

| Model | When to use |
|-------|-------------|
| `claude-haiku-4-5-20251001` | Mechanical tasks: known file, known line, add/change one thing. T1, T5. |
| `claude-sonnet-4-6` | Multi-file implementation, test writing, reading + faithfully extending existing code. T2, T3, T4. |
| `claude-opus-4-8` | Escalate from Sonnet when: output deviates from existing style, coverage gap analysis is non-obvious, or SQL/async edge cases need deeper reasoning. |

No Gemini models are used for these tasks. All five tasks are implementation
work against a known codebase — they require accurate file reads and precise
edits. Gemini is better suited to research, design, or review passes.

If you want a Gemini 3.1 Pro review pass after T3 (metrics dashboard) to
sanity-check the HTML/UI before merge, that is a valid optional step. Format
that prompt as a single fenced code block with the model in the header per
the established Gemini prompt convention.

---

## Completion Criteria — v2 Done

BIND v2 is complete when all of the following are true:

- [ ] T1 merged: CI audits both production and dev deps
- [ ] T2 merged: `/health` reports domain probe status; daemon warns on startup
- [ ] T3 merged: `/metrics` page live and nav-linked; scrape runs recorded
- [ ] T4 merged: `pytest --cov-fail-under=75` passes in CI
- [ ] T5 merged (optional): Codecov badge live on README
- [ ] All tests passing: `pytest` exits 0 on main
- [ ] Type-clean: `mypy src/` exits 0
- [ ] Lint-clean: `ruff check src/ tests/` exits 0
- [ ] Git tag `v2.0.0` pushed

At that point, update `.raiden/state/CURRENT_STATE.md` to reflect v2.0.0 and
close this plan.
