```claude-sonnet
You are adding pytest tests to the BIND project to improve code coverage.
Working directory: /mnt/e/BIND
Activate the venv before running anything: source .venv/bin/activate

## Your task

Create a new file `tests/test_security_core.py` covering the uncovered branches of
pure utility functions in `src/security.py`. These functions do NOT require a Flask
request context.

Read `src/security.py` and `tests/test_security.py` before writing any tests so
you understand what is already covered.

---

## Critical setup — credential file isolation (REQUIRED)

`src/security.py` has this module-level constant set at import time:

```python
CREDENTIALS_FILE = get_credentials_path()  # evaluates at import, not at call time
```

Every test in this file MUST redirect that constant to a temp path. Add this
autouse fixture at the top of the test file:

```python
import pytest

@pytest.fixture(autouse=True)
def isolated_credentials(tmp_path, monkeypatch):
    cred_path = str(tmp_path / "credentials.json")
    monkeypatch.setattr("src.security.CREDENTIALS_FILE", cred_path)
    return cred_path
```

Without this fixture, tests either read/write the real credentials.json on disk
or fail with cryptic permission errors.

---

## Targets and what to test

### 1. `get_base_dir()` — the `/opt/bind` branch

`get_base_dir` returns `/opt/bind` when that path exists, otherwise it returns the
project root derived from `__file__`. In test environments, `/opt/bind` never exists,
so the first branch is uncovered.

Test: monkeypatch `os.path.exists` to return `True` when called with `/opt/bind`.
Assert the return value is `"/opt/bind"`.

```python
def test_get_base_dir_returns_opt_bind_when_it_exists(monkeypatch):
    monkeypatch.setattr("os.path.exists", lambda p: p == "/opt/bind")
    from src.security import get_base_dir
    assert get_base_dir() == "/opt/bind"
```

---

### 2. `_rotate_log_if_needed()` — the rotation branch

`_rotate_log_if_needed(log_path, max_lines=N)` reads the file and rewrites it with
only the last N lines when the line count exceeds N. The rewrite branch is uncovered.

Test: write a temp file with more than `max_lines` lines, call
`_rotate_log_if_needed(path, max_lines=3)`, assert the file now has exactly 3 lines
and contains the last 3 lines of the original content.

---

### 3. `_migrate_credentials()` — v1 → v2 migration

`_migrate_credentials` adds v2 fields to a v1 credential dict and calls
`_save_credentials_raw` to persist it. The branch body (lines that add the new fields)
is uncovered.

Test: pass in a dict with `"version": 1` and a password hash. Assert the returned
dict has `"version": 2` and contains the keys `"failed_attempts"`, `"locked_until"`,
`"last_login"`, `"last_login_ip"`. Use the `isolated_credentials` fixture so
`_save_credentials_raw` writes to `tmp_path` instead of the real filesystem.

---

### 4. `_save_credentials_raw()` — OSError returns False

`_save_credentials_raw` returns `False` when the file write raises `OSError`.
The except branch is uncovered.

Test: patch `src.security.open` (not `builtins.open`) to raise `OSError`.
Call `_save_credentials_raw({"version": 2})`. Assert it returns `False`.

```python
from unittest.mock import patch

def test_save_credentials_raw_returns_false_on_oserror(isolated_credentials):
    from src.security import _save_credentials_raw
    with patch("src.security.open", side_effect=OSError("permission denied")):
        assert _save_credentials_raw({"version": 2}) is False
```

---

### 5. `is_account_locked()` — lockout expired branch

When `locked_until` is a past timestamp, `is_account_locked` clears the lockout in
the credentials file and returns `(False, None)`. This "expiry cleanup" branch is
uncovered.

Test: write a credentials file via `isolated_credentials` that has `locked_until` set
to a timestamp 2 hours in the past (use `datetime.now(timezone.utc) - timedelta(hours=2)`
formatted as ISO). Call `is_account_locked()`. Assert it returns `(False, None)`. Assert
the credentials file no longer has a non-None `locked_until`.

---

### 6. `is_account_locked()` — ValueError / TypeError branch

When `locked_until` contains an unparseable value, `is_account_locked` catches the
exception and returns `(False, None)`.

Test: write a credentials file with `"locked_until": "not-a-date"`. Call
`is_account_locked()`. Assert it returns `(False, None)`.

---

### 7. `get_allowed_networks()` — env var branch

When `BIND_ALLOWED_IPS` is set, `get_allowed_networks` returns the parsed list from
the env var instead of the defaults.

Test: set `BIND_ALLOWED_IPS` to `"10.1.2.0/24,172.31.0.0/16"` via monkeypatch.
Assert `get_allowed_networks()` returns `["10.1.2.0/24", "172.31.0.0/16"]`.

---

### 8. `is_ip_allowed()` — invalid network in allowlist

When a network string in the allowlist is not valid CIDR, `is_ip_allowed` catches
the `ValueError` and continues to the next entry. This `continue` branch is uncovered.

Test: monkeypatch `get_allowed_networks` to return `["not-valid-cidr", "10.0.0.0/8"]`.
Call `is_ip_allowed("10.0.0.1")`. Assert it returns `True` (the bad entry is skipped,
the valid entry still matches).

---

### 9. `get_client_ip()` — invalid remote_addr

When `req.remote_addr` is not a valid IP address string (e.g. `"not-an-ip"`),
`get_client_ip` catches the `ValueError` and returns `"0.0.0.0"`.

Test: create a simple mock request object with `remote_addr = "not-an-ip"`. Call
`get_client_ip(mock_req)`. Assert it returns `"0.0.0.0"`.

```python
from unittest.mock import MagicMock

def test_get_client_ip_returns_fallback_on_invalid_remote_addr():
    from src.security import get_client_ip
    req = MagicMock()
    req.remote_addr = "not-an-ip"
    assert get_client_ip(req) == "0.0.0.0"
```

---

## Validation

Run the new file:
```bash
python -m pytest tests/test_security_core.py -v --cov=src/security --cov-report=term-missing
```

All tests must pass. Report the final coverage percentage and any lines still missing.
Then run the full suite to confirm no regressions:
```bash
python -m pytest tests/ -q --tb=short 2>&1 | tail -10
```
```
