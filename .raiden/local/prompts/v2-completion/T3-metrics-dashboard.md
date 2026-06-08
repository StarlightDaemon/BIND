# T3 — Metrics Dashboard

## Prompt ID

`bind.v2.T3.metrics-dashboard.v1`

## Purpose

Add a visual metrics page (`/metrics`) to the web UI backed by an extended
`MagnetStore.stats()` and a new `scrape_runs` table that records per-run
outcomes. This is the last unfinished item from the ROADMAP.md v2.0 feature list.

## Agent Type

**Claude Code** — multi-file: DB schema, Flask route, Jinja2 template, tests.

## Model

**Primary:** `claude-sonnet-4-6`
Rationale: Full-stack Python/Flask/SQLite/HTML work across 4–5 files. Sonnet
reliably handles this scope while staying faithful to an existing UI theme
without being prompted to over-engineer. Opus is unnecessarily expensive here.

**Secondary:** `claude-opus-4-8`
Use if Sonnet produces a template that deviates significantly from the Vesper
theme, or if the SQL window queries for 7/30-day counts come out wrong.

## Phase

Phase 1 — runs **in parallel** with T1 and T2.

Overlap note: T2 also modifies `/health` in `src/rss_server.py`. T3 adds a new
`/metrics` route to the same file. These are non-overlapping edits. If running
sequentially, apply T2 first, then T3 — the merge is trivial.

---

## Prompt

You are working in the repository at `/Users/dante/Citadel/BIND`.

BIND is a Python audiobook metadata daemon (v1.7.1). It scrapes AudioBookBay,
stores records in a SQLite database via `MagnetStore` (WAL + FTS5), and serves
a Flask web UI styled with the "Vesper" theme (dark, minimal, monospace).

### Key Files

- `src/core/storage.py` — `MagnetStore`; `stats()` at line 165
- `src/rss_server.py` — Flask app; all routes; `store` module-level instance
- `src/bind.py` — daemon; `run_job_with_timeout()` wraps each scrape cycle
- `src/templates/` — Jinja2 templates; inspect existing ones for Vesper style
- `src/static/` — CSS/JS assets

### Current `store.stats()` Output

```python
{
    "total": int,
    "today": int,
    "last_date": str | None,
}
```

### Task

#### 1. Extend `MagnetStore.stats()` in `src/core/storage.py`

Add two new keys using SQLite date arithmetic — no Python date loops:

```sql
SELECT COUNT(*) FROM magnets
WHERE date(collected_date) >= date('now', '-6 days')
```

```sql
SELECT COUNT(*) FROM magnets
WHERE date(collected_date) >= date('now', '-29 days')
```

Return them as `"last_7_days"` and `"last_30_days"`. Existing keys are
unchanged — this is additive only.

#### 2. Add `scrape_runs` table in `src/core/storage.py`

In `_init_schema()`, add:

```sql
CREATE TABLE IF NOT EXISTS scrape_runs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    run_at     TEXT NOT NULL,
    result     TEXT NOT NULL CHECK(result IN ('success', 'failure', 'empty')),
    items_new  INTEGER NOT NULL DEFAULT 0,
    duration_s REAL    NOT NULL DEFAULT 0.0
)
```

Add `record_scrape_run(self, result: str, items_new: int, duration_s: float) -> None`
to `MagnetStore`. It inserts one row with `run_at = datetime.now(timezone.utc).isoformat()`.

#### 3. Instrument `src/bind.py`

In `run_job_with_timeout()` (or the inner `job()` function it calls), wrap the
scrape call with a timer:

```python
import time as _time
t0 = _time.monotonic()
try:
    new_count = scraper.run()          # or however job() gets new items
    result = "success" if new_count > 0 else "empty"
    items_new = new_count
except Exception as exc:
    result = "failure"
    items_new = 0
    raise
finally:
    store.record_scrape_run(result, items_new, _time.monotonic() - t0)
```

Adapt the variable names to match the existing code — read `bind.py` first
before editing. Do not change the existing retry/circuit-breaker flow; only
wrap it with timing and recording.

#### 4. Add `/metrics` route to `src/rss_server.py`

```python
@app.route("/metrics")
@requires_auth
def metrics_view() -> str:
    db_stats = store.stats()
    runs = store.conn.execute(
        "SELECT run_at, result, items_new, duration_s "
        "FROM scrape_runs ORDER BY id DESC LIMIT 30"
    ).fetchall()
    total_runs = len(runs)
    success_count = sum(1 for r in runs if r[1] == "success")
    success_rate = round(success_count / total_runs * 100) if total_runs else None
    return render_template(
        "metrics.html",
        stats=db_stats,
        runs=runs,
        success_rate=success_rate,
        now=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
```

Use `store._conn` or however the connection is exposed — check `storage.py`
for the attribute name before writing.

#### 5. Create `src/templates/metrics.html`

Read two or three existing templates first to understand the Vesper theme
(dark background, monospace font, sparse layout). Match that style exactly —
same `<head>`, same font stack, same nav structure.

The page must show:
- **Counts card**: Total, Today, Last 7 days, Last 30 days, Last collected date
- **Scrape history table**: run_at (formatted local time), result (color-coded
  badge: success=green `#4caf50`, failure=red `#f44336`, empty=yellow `#ff9800`),
  new items, duration in seconds (1 decimal place)
- **Success rate**: e.g. "87% success rate over last 30 runs" or "No runs recorded"
  if table is empty
- **Footer**: "Last updated: {{ now }}"

No JavaScript. No new CSS files. Use only inline styles or classes already
present in the existing templates.

#### 6. Add nav link

In whichever template file contains the site navigation, add a link to
`/metrics` alongside the existing nav items.

#### 7. Tests in `tests/test_metrics.py`

- Test `store.stats()` returns `last_7_days` and `last_30_days` keys
- Test `record_scrape_run("success", 5, 1.23)` inserts a row queryable by
  `SELECT COUNT(*) FROM scrape_runs`
- Test `GET /metrics` returns HTTP 200 for an authenticated client
  (follow the existing auth test pattern — check `tests/` for how sessions
  are set up)

Use `tmp_path` + real SQLite for storage tests (no mocking sqlite3).

### Exit Criteria

- `store.stats()` returns `last_7_days` and `last_30_days` without breaking
  existing callers
- `scrape_runs` table is created by `_init_schema()`
- `record_scrape_run()` inserts rows correctly
- `bind.py` records each scrape cycle outcome
- `/metrics` renders HTML (auth-gated), no errors on empty DB
- `metrics.html` matches Vesper theme; color-coded result badges present
- Nav link to `/metrics` added
- `tests/test_metrics.py` passes
- Full `pytest` suite passes with no regressions
- `mypy src/` passes
- `ruff check src/ tests/` passes
