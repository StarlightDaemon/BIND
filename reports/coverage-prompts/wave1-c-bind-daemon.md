# Group C — bind.py: Daemon Command Internals

**Model: Claude Sonnet**  
**No dependencies** — runs independently, appends to `tests/test_bind_daemon.py`  
**Working directory:** `/mnt/e/BIND`

## Why Claude for this group

This group requires mocking across signal handling, `concurrent.futures.ThreadPoolExecutor`, and the `schedule` library simultaneously. The `run_job_with_timeout` inner function holds live state through a dict (`_last_future`) that must be threaded correctly through mocks. Getting this wrong produces tests that pass vacuously.

## Your task

Append new test classes to `tests/test_bind_daemon.py` covering the untested
branches in the `daemon` Click command. Do NOT modify existing tests.

## Coverage targets

```
src/bind.py   Missing: 87-88, 128-132, 134-135, 147-216
```

Key gaps:
- 87–88   → `run_job` — `add_magnet` returns False (race-condition duplicate, `skipped_dupes` path)
- 128–132 → `daemon()` — config key already in `os.environ` (mismatch log branch)
- 134–135 → `daemon()` — `config_mgr.read_config()` raises (warning log path)
- 147–151 → `daemon()` — `MagnetStore(db_path)` raises `RuntimeError` → `sys.exit(1)`
- 158–161 → `daemon()` — `signal_handler` function body (sets shutdown flag)
- 171–196 → `daemon()` — `run_job_with_timeout()` body (prev job still running, normal run, timeout, exception, finally block)
- 199–204 → `daemon()` — probe result is `"unreachable"` or `"wrong_content"` → warning logged
- 206–216 → daemon loop (`schedule.run_pending` + `while shutdown_requested`) — acceptable to leave under pragma

## Key files to read before writing

- `src/bind.py` full file
- `tests/test_bind_daemon.py` full file (existing tests to understand patterns)

## Critical facts

1. **`run_job` add_magnet returns False (lines 85–88):** `store.add_magnet` returning `False` (not raising) increments `skipped_dupes`, not `failed_saves`. Mock `store.add_magnet` to return `False`, assert `store.stats()["total"] == 0`.

2. **`daemon` command isolation pattern:** Use `CliRunner().invoke(cli, ["daemon", "--db-path", ...])`. The daemon loop runs forever unless interrupted, so you MUST break it. The cleanest approach:
   - Patch `schedule.every` to return a mock (prevents real scheduling).
   - Patch the inner `run_job_with_timeout` indirectly by patching `concurrent.futures.ThreadPoolExecutor`.
   - Patch `time.sleep` to raise `KeyboardInterrupt` or set `shutdown_requested["flag"] = True` after first call to break the loop.

3. **Testing the config mismatch branch (lines 128–132):** Pre-set an env var to a value that differs from what `read_config()` returns. Example: `os.environ["SCRAPE_INTERVAL"] = "30"`, `read_config()` returns `{"SCRAPE_INTERVAL": "60"}`. The debug log `"Config mismatch for..."` should appear in `caplog`.

4. **Testing `MagnetStore` RuntimeError → exit 1 (lines 147–151):**
   ```python
   with patch("src.bind.MagnetStore", side_effect=RuntimeError("db locked")):
       result = CliRunner().invoke(cli, ["daemon", "--db-path", str(tmp_path / "x.db")])
   assert result.exit_code == 1
   ```

5. **Testing `signal_handler` directly (lines 158–161):** The `signal_handler` closure is defined inside `daemon()` and is not importable. Patch `signal.signal` to capture all registered handlers (e.g. store calls in a list). After `CliRunner().invoke` completes, assert that both `signal.SIGTERM` and `signal.SIGINT` were registered. Verifying registration is sufficient — do not call the captured handler.

6. **Testing `run_job_with_timeout` (lines 171–196):**

`run_job_with_timeout` is an inner function — not importable. But it is called **directly
on line 208** immediately after being scheduled, before the while loop. This means every
`CliRunner().invoke(cli, ["daemon", ...])` call hits it automatically. No schedule
interception is needed to reach it.

**Setup pattern for all three branches:**

Patch `concurrent.futures.ThreadPoolExecutor` so its `submit()` returns a `MagicMock`
Future you control. Patch `time.sleep` to raise `KeyboardInterrupt` to exit the while
loop after the direct call completes.

```python
from unittest.mock import MagicMock, patch
import concurrent.futures
from click.testing import CliRunner
from src.bind import cli

mock_future = MagicMock()
mock_future.done.return_value = True
mock_future.result.return_value = 3  # success path

with patch("concurrent.futures.ThreadPoolExecutor") as MockTPE:
    MockTPE.return_value.submit.return_value = mock_future
    with patch("src.bind.time.sleep", side_effect=KeyboardInterrupt):
        with patch("src.bind.schedule"):  # suppress real scheduling
            result = CliRunner().invoke(cli, ["daemon", "--db-path", str(tmp_path / "x.db")])
```

**Timeout path:** set `mock_future.result.side_effect = concurrent.futures.TimeoutError()`.
Assert the timeout warning is logged in `caplog`.

**Unexpected exception path:** set `mock_future.result.side_effect = ValueError("boom")`.
Assert the error is logged in `caplog`.

**Previous job still running path:** requires a second call to `run_job_with_timeout`.
After the direct call on line 208 stores a not-done Future in `_last_future`, the while
loop's `schedule.run_pending()` must fire it again. Use this pattern to capture and
replay the job function:

```python
captured = {}

def capture_do(fn):
    captured["job"] = fn
    return MagicMock()

def call_once_then_stop():
    if captured.get("job"):
        captured["job"]()
        captured.pop("job")
    raise KeyboardInterrupt

mock_future = MagicMock()
mock_future.done.return_value = False  # not done — triggers the warning

with patch("src.bind.schedule") as mock_sched:
    mock_sched.every.return_value.minutes.do.side_effect = capture_do
    mock_sched.run_pending.side_effect = call_once_then_stop
    with patch("concurrent.futures.ThreadPoolExecutor") as MockTPE:
        MockTPE.return_value.submit.return_value = mock_future
        result = CliRunner().invoke(cli, ["daemon", "--db-path", str(tmp_path / "x.db")])

assert "Previous job is still running" in caplog.text
```

Do NOT run the daemon in a real thread.

7. **Probe warning (lines 199–204):** Patch `BindScraper.probe_target` to return `"unreachable"`. Break the loop immediately after. Assert the warning log contains `"unreachable"`.

8. **The `while` loop (lines 211–213):** The `# pragma: no cover` comment is already present in the source at lines 211–213. Do NOT add or remove pragma comments from any source file. No test needed for these lines.

## Classes to write

```python
class TestRunJobEdgeCases:
    # test_add_magnet_returns_false_counts_as_dupe
    #   mock store.add_magnet → False, assert total == 0, skipped_dupes implied by no failed count

class TestDaemonConfigLoading:
    # test_config_key_already_in_env_logs_mismatch
    # test_config_load_exception_logs_warning

class TestDaemonStartupFailures:
    # test_magnet_store_runtime_error_exits_1

class TestDaemonSignalRegistration:
    # test_signal_handlers_registered_for_sigterm_and_sigint

class TestDaemonProbeWarning:
    # test_probe_unreachable_logs_warning
    # test_probe_wrong_content_logs_warning

class TestRunJobWithTimeout:
    # test_skips_run_when_previous_job_still_running
    # test_logs_warning_on_timeout
    # test_logs_error_on_unexpected_exception
```

## Validation

After writing, run:
```bash
python -m pytest tests/test_bind_daemon.py -v --cov=src/bind --cov-report=term-missing
```
Target: `src/bind.py` coverage above 78%. All tests must pass.
Report the final coverage line from the output.
