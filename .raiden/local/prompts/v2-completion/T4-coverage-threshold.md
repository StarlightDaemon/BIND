# T4 — Coverage Threshold + Storage Tests

## Prompt ID

`bind.v2.T4.coverage-threshold.v1`

## Purpose

Raise the CI coverage gate from 40% to 75% by writing targeted real-database
tests for `src/core/storage.py` (the critical SQLite layer added in v1.7.0)
and filling other gaps identified by a fresh coverage run.

## Agent Type

**Claude Code** — test authoring + config change.

## Model

**Primary:** `claude-sonnet-4-6`
Rationale: Systematic test writing against a known API. Requires reading
current coverage output, identifying gaps in specific modules, and writing
focused tests. Sonnet handles this reliably. The storage tests use real SQLite
(no mocks) which requires accurate SQL fixture setup — Sonnet is solid here.

**Secondary:** `claude-opus-4-8`
Use if coverage after initial tests is still stuck below 70% and gap analysis
requires reasoning across several interacting modules to find the right paths
to exercise.

## Phase

Phase 2 — runs **after Phase 1 is fully merged and CI is green**.

Do not start this task until T1, T2, and T3 are merged. Reason: T2 adds
`probe_target()` and T3 adds `scrape_runs` + `record_scrape_run()` — both
are new uncovered code paths. Starting coverage work before those land means
the threshold may be set correctly for Phase 1 code but fail immediately when
Phase 2 code is added.

---

## Prompt

You are working in the repository at `/Users/dante/Citadel/BIND`.

BIND is a Python audiobook metadata daemon (v1.7.1) with Phase 1 changes
(T1/T2/T3) already merged. The test suite currently uses `--cov-fail-under=40`
in CI (`.github/workflows/ci.yml`). The goal is to reach 75%.

### Step 0 — Baseline

Before writing any tests, run:

```bash
pytest --cov=src --cov-report=term-missing 2>&1 | tee /tmp/coverage-baseline.txt
```

Read the output. Note the per-file coverage percentages, especially for:
- `src/core/storage.py` — critical SQLite layer
- `src/core/retry.py`
- `src/core/egress_manager.py`
- `src/core/schema_monitor.py`
- `src/core/scraper.py`
- `src/security.py`

Do not proceed until you have the baseline numbers in hand.

### Step 1 — `tests/test_storage_extended.py`

Write real-database tests using `tmp_path` pytest fixture. Do **not** mock
`sqlite3` — these must run against a real SQLite file.

Required test cases:

**Schema**
- After `MagnetStore(tmp_path / "test.db")`, both `magnets` and `scrape_runs`
  tables exist (query `sqlite_master`)

**`add_magnet()`**
- Inserting a record increases `COUNT(*)` in `magnets` by 1
- Inserting the same `info_hash` twice does not raise and does not create a
  duplicate row (idempotent)

**`has_hash()`**
- Returns `True` for a hash that was added
- Returns `False` for a hash that was not added

**`recent(limit=N)`**
- Returns at most N rows
- With 5 rows inserted, `recent(limit=3)` returns 3
- Rows are ordered by insertion recency (last in, first out)

**`search(query)`**
- A query matching the title of an inserted record returns that record
- An empty-string query returns all records

**`stats()`**
- After inserting 3 records with `collected_date = today`, `stats()["today"]`
  equals 3
- `stats()["last_7_days"]` and `stats()["last_30_days"]` keys exist and are
  integers

**`record_scrape_run()`**
- After calling `record_scrape_run("success", 5, 1.23)`, a `SELECT COUNT(*)`
  on `scrape_runs` returns 1
- The row has `result="success"`, `items_new=5`

**WAL probe**
- `MagnetStore(tmp_path / "probe.db")` does not raise (WAL mode works on a
  local path)

### Step 2 — Fill Remaining Gaps

After writing Step 1 tests, re-run coverage. If aggregate is below 70%, look
at the term-missing output and write a `tests/test_resilience_extended.py`
covering missed lines in `retry.py`, `schema_monitor.py`, or
`egress_manager.py`.

Use `pytest-mock` / `mocker.patch` for external network calls. Do not
write tests that make real HTTP requests.

For `src/core/scraper.py` if below 60%: add tests for `probe_target()`
result variants if not already covered by T2's `test_scraper_probe.py`.

Stop when `pytest --cov=src --cov-fail-under=75` passes.

### Step 3 — Raise the Threshold

Once the suite passes at 75%:

1. In `.github/workflows/ci.yml`, change `--cov-fail-under=40` to
   `--cov-fail-under=75`

2. In `pyproject.toml` `[tool.pytest.ini_options]` `addopts`, add
   `--cov-fail-under=75` (so local runs enforce the same gate as CI)

### Exit Criteria

- `pytest --cov=src --cov-report=term-missing --cov-fail-under=75` passes
- `tests/test_storage_extended.py` exists with ≥12 test cases using real SQLite
- CI threshold in `.github/workflows/ci.yml` is `75`
- `pyproject.toml` addopts includes `--cov-fail-under=75`
- No existing tests broken
- `mypy src/` passes
- `ruff check src/ tests/` passes
