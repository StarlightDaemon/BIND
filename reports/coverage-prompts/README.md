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
| A | [wave1-a-rss-authenticated-routes.md](wave1-a-rss-authenticated-routes.md) | 🟣 Gemini 3.1 Pro | +5.5% | ✅ Done |
| C | [wave1-c-bind-daemon.md](wave1-c-bind-daemon.md) | 🔵 Claude Sonnet | +2.5% | ✅ Done |
| D | [wave1-d-scraper-network.md](wave1-d-scraper-network.md) | 🟣 Gemini 3.1 Pro | +2.0% | ✅ Done |
| F-core | [wave1-f-core.md](wave1-f-core.md) | 🔵 Claude Sonnet | +0.8% | ✅ Done |
| F-flask | [wave1-f-flask.md](wave1-f-flask.md) | 🔵 Claude Sonnet | +0.8% | ✅ Done |
| G | [wave1-g-easy-wins.md](wave1-g-easy-wins.md) | 🟡 Gemini 3 Flash | +0.8% | ✅ Done |

---

## Wave 2 — Ready to ship

B and E are reviewed and ready. Each appends to a file Wave 1 already modified —
do not run until the Wave 1 commit is on main.

| | Prompt | Model | Est. gain | Prereq |
|---|---|---|---|---|
| B | [wave2-b-rss-csrf-setup.md](wave2-b-rss-csrf-setup.md) | 🔵 Claude Sonnet | +1.5% | A committed ✅ |
| E | [wave2-e-scraper-parse-strategies.md](wave2-e-scraper-parse-strategies.md) | 🟡 Gemini 3 Flash | +1.2% | D committed ✅ |

Both can run simultaneously. Expected coverage after Wave 2: 98%+.

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

| | Model | Best for |
|---|---|---|
| 🔵 | Claude Sonnet | Session mechanics, signals, security reasoning, complex mocks |
| 🟣 | Gemini 3.1 Pro | Repeated route patterns, large multi-file context |
| 🟡 | Gemini 3 Flash | Pure functions, simple fixtures, no complex mocking |
