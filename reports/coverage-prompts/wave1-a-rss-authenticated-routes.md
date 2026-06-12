```gemini-3.1-pro
You are adding pytest tests to the BIND project to improve code coverage.
Working directory: /mnt/e/BIND
Activate the venv before any shell commands: source .venv/bin/activate

## Your task

Append new test classes to `tests/test_rss_server.py` covering the six authenticated
routes and the `check_daemon_status` helper in `src/rss_server.py`.
Do NOT modify any existing tests or fixtures. Append only.

## What is already tested (do not duplicate)

`/health`, `/feed.xml`, `/`, `/magnets` (basic), `_resolve_secret_key`, `_date_to_rfc2822`

## Coverage targets — missing lines to cover

```
src/rss_server.py   Missing: 189-190, 273-303, 315-326, 338-361, 394-409, 420-438, 441-457, 460-477
```

Map to routes:
- 189-190  → `/magnets` with `?page=abc` (ValueError branch)
- 273-303  → `/settings` GET + POST (config save + daemon restart branches)
- 315-326  → `/settings/trackers` POST (success + exception branches)
- 338-361  → `/logs` GET with `?log=security` and `?log=daemon`, file exists and missing
- 394-409  → `/settings/password` POST (mismatch + change_password success/fail)
- 420-438  → `check_daemon_status()` (online, offline, unknown branches)
- 441-457  → `/metrics` GET
- 460-477  → `/api/stats` GET

## Key infrastructure (read these files before writing)

- `tests/conftest.py` — fixture definitions
- `src/rss_server.py` lines 267-477 — the routes you are testing

## Critical facts

1. `BIND_AUTH_ENABLED=false` is set in conftest so `@requires_auth` lets all requests through — no login session needed.
2. The `mock_setup_complete` autouse fixture makes `is_setup_complete()` return True — no setup redirect.
3. The `client` fixture already injects a `fresh_store`; use it as-is.
4. `config_manager` and `tracker_manager` are module-level singletons in `rss_server.py`. Monkeypatch them where needed.
5. For `/settings` POST, mock `config_manager.write_config` and `config_manager.restart_daemon` to control success/failure branches.
6. For `check_daemon_status`, call it directly (it is a plain function, not a route). Provide a real tmp log file via `tmp_path` to exercise the online/offline path; test the missing-file path and the exception path.
7. `/metrics` calls `store._conn.execute(...)` directly — monkeypatch `store` with `fresh_store` (already done by `client` fixture) and make sure `fresh_store` has at least one `scrape_runs` row via `fresh_store.record_scrape_run(...)`.
8. `/api/stats` calls `check_daemon_status()` internally — patch `src.rss_server.check_daemon_status` to return a fixed tuple.
9. All POST routes expect a CSRF token. Patch `validate_csrf_token` to a no-op for every POST test — do not attempt to generate a real token, it requires Flask session context and is fragile:
   ```python
   monkeypatch.setattr("src.rss_server.validate_csrf_token", lambda: None)
   ```
   Include any dummy string as `csrf_token` in the POST form data so the route handler doesn't complain about a missing field.

## Classes to write

```python
class TestMagnetsEdgeCases:
    # test_magnets_invalid_page_defaults_to_1 — GET /magnets?page=abc should return 200

class TestSettingsRoute:
    # test_settings_get_returns_200
    # test_settings_post_save_success_and_restart_success
    # test_settings_post_save_success_but_restart_fails
    # test_settings_post_write_fails

class TestSettingsTrackersRoute:
    # test_settings_trackers_post_success
    # test_settings_trackers_post_exception

class TestLogsRoute:
    # test_logs_security_log_exists
    # test_logs_security_log_missing
    # test_logs_daemon_log_type

class TestChangePasswordRoute:
    # test_change_password_mismatch
    # test_change_password_success
    # test_change_password_current_incorrect

class TestCheckDaemonStatus:
    # test_status_online  (log file mtime recent)
    # test_status_offline (log file mtime old)  ← use os.utime() — see note below
    # test_status_unknown_no_log_file
    # test_status_unknown_on_exception

# NOTE for test_status_offline:
# Do NOT rely on file creation time. Use os.utime() to force the mtime to a past value:
#
#   import os, time
#   log_file = tmp_path / "bind.log"
#   log_file.write_text("log line")
#   past = time.time() - 7200  # 2 hours ago
#   os.utime(log_file, (past, past))
#
# Then call check_daemon_status() and assert it returns ("offline", ...).
# Without os.utime(), the test is non-deterministic: a freshly-created file will
# have a current mtime and the offline branch will never trigger.

class TestMetricsRoute:
    # test_metrics_returns_200
    # test_metrics_shows_run_data

class TestApiStatsRoute:
    # test_api_stats_returns_json
    # test_api_stats_has_expected_keys
```

## Validation

After writing, run:
```
python -m pytest tests/test_rss_server.py -v --cov=src/rss_server --cov-report=term-missing
```
Target: `src/rss_server.py` coverage above 80%. All tests must pass.
Report the final coverage line from the output.
```
