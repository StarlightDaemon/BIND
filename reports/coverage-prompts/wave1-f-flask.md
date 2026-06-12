```claude-sonnet
You are adding pytest tests to the BIND project to improve code coverage.
Working directory: /mnt/e/BIND
Activate the venv before running anything: source .venv/bin/activate

## Your task

Append new test classes to `tests/test_security.py` covering uncovered branches of
functions in `src/security.py` that either call `get_client_ip(request)` internally
or require the Flask request context.

Read `src/security.py` and `tests/test_security.py` before writing any tests.

---

## Critical setup — credential file isolation (REQUIRED)

`src/security.py` has this module-level constant set at import time:

```python
CREDENTIALS_FILE = get_credentials_path()  # evaluates at import, not at call time
```

Add this autouse fixture at the top of the new test class block (or at module level
in test_security.py if it is not already present):

```python
@pytest.fixture(autouse=True)
def isolated_credentials(tmp_path, monkeypatch):
    cred_path = str(tmp_path / "credentials.json")
    monkeypatch.setattr("src.security.CREDENTIALS_FILE", cred_path)
    return cred_path
```

Without this fixture, tests write to real credential paths, contaminate each other,
and produce cryptic failures that have nothing to do with the code under test.

**Check `tests/test_security.py` first.** If this fixture is already defined there,
do not add a duplicate — just confirm it is `autouse=True` scoped to cover your new tests.

---

## Flask context

Functions that call `get_client_ip(request)` internally raise
`RuntimeError: Working outside of request context` when called bare in a test.

The `flask_app` fixture is defined in `tests/conftest.py` and provides the Flask app
with `TESTING = True`. Use it for two patterns:

**Pattern A — direct function call (for functions that aren't routes):**
```python
def test_something(flask_app, isolated_credentials):
    with flask_app.test_request_context("/"):
        from src.security import save_credentials
        result = save_credentials("admin", "Password1!")
        assert result == (True, "Account created successfully.")
```

**Pattern B — test client (for middleware and decorator tests):**
```python
def test_something(flask_app, isolated_credentials):
    client = flask_app.test_client()
    response = client.get("/settings")
    assert response.status_code == ...
```

---

## Targets and what to test

### 1. `save_credentials()` — save-fails branch (line ~229)

When `_save_credentials_raw` returns `False`, `save_credentials` returns
`(False, "Failed to save credentials.")`.

Test: patch `src.security._save_credentials_raw` to return `False`. Call
`save_credentials` inside `flask_app.test_request_context("/")` with a valid
username and password. Assert the result is `(False, "Failed to save credentials.")`.

---

### 2. `change_password()` — all branches (lines ~243–275)

`change_password` has four outcomes:
- No credentials file → `(False, "No credentials found.")`
- Wrong current password → `(False, "Current password is incorrect.")`
- Invalid new password → `(False, "Password must be at least 8 characters.")`
- Success → `(True, "Password changed successfully.")`
- Save fails → `(False, "Failed to save new password.")`

For each test: set up `isolated_credentials` to point to a tmp path. Write a valid
credentials JSON to that path (use `werkzeug.security.generate_password_hash`) so
`load_credentials()` returns a populated dict. Call `change_password` inside
`flask_app.test_request_context("/")`.

For the no-credentials case: leave the `isolated_credentials` path empty (don't write
the file) so `is_setup_complete()` returns False and `load_credentials()` returns `{}`.

---

### 3. `record_successful_login()` — no-creds early return (line ~338)

When `load_credentials()` returns an empty dict, `record_successful_login` returns
immediately without error. This early return branch is uncovered.

Test: with `isolated_credentials` pointing to a nonexistent file, call
`record_successful_login("127.0.0.1")`. Assert it returns `None` and does not raise.
No Flask context needed here since the function takes `ip: str` directly.

---

### 4. `verify_credentials()` — no-creds and locked branches (lines ~358, ~363)

- `verify_credentials` returns `False` immediately when `load_credentials()` is empty.
- `verify_credentials` returns `False` immediately when `is_account_locked()` is True.

For both: no Flask context needed (function takes `ip: str` directly).

For the no-creds branch: leave credentials file empty. Call
`verify_credentials("admin", "Password1!", "127.0.0.1")`. Assert it returns `False`.

For the locked branch: write a credentials file with `locked_until` set to a future
timestamp. Call `verify_credentials("admin", "Password1!", "127.0.0.1")`. Assert
it returns `False`.

---

### 5. `check_auth()` — locked and setup-not-complete branches (lines ~493–504)

`check_auth` uses `get_client_ip(request)` — must run inside request context.

- When account is locked → returns `False`
- When setup is not complete → returns `False`

Use `flask_app.test_request_context("/")` for both. For the locked branch, write
credentials with a future `locked_until`. For the setup-not-complete branch, leave
the credentials file absent.

---

### 6. `requires_auth` decorator — locked and no-auth branches (lines ~526–548)

`requires_auth` is applied to routes in `src/rss_server.py`. Test it by calling
a protected route through the test client.

`BIND_AUTH_ENABLED=false` is set in conftest, which makes the decorator pass all
requests through. To test the decorator's locked/unauthorized branches, you must
temporarily override that env var:

```python
def test_requires_auth_returns_403_when_locked(flask_app, isolated_credentials, monkeypatch):
    import json
    from datetime import datetime, timedelta, timezone
    monkeypatch.setenv("BIND_AUTH_ENABLED", "true")
    lock_time = (
        datetime.now(timezone.utc) + timedelta(hours=1)
    ).isoformat().replace("+00:00", "Z")
    with open(isolated_credentials, "w") as f:
        json.dump({
            "version": 2, "username": "admin",
            "password_hash": "irrelevant",
            "failed_attempts": 5, "locked_until": lock_time,
            "last_login": None, "last_login_ip": None,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }, f)
    client = flask_app.test_client()
    response = client.get("/settings")
    assert response.status_code == 403
    assert b"locked" in response.data.lower()
```

Also test the no-auth 401 branch: with `BIND_AUTH_ENABLED=true` and a valid
credentials file but no `Authorization` header, assert the response is 401.

---

### 7. `ip_allowlist_middleware` — filter-disabled and blocked-IP branches

`ip_allowlist_middleware` registers a `before_request` handler. Test it through
the Flask test client.

- Filter disabled: set `BIND_IP_FILTER=false` (monkeypatch). Assert that a request
  from an external IP still gets a 200 (not a 403).
- Blocked IP: set `BIND_IP_FILTER=true` (monkeypatch env). Make the test client
  send a request with `REMOTE_ADDR` set to a non-private IP (e.g. `"1.2.3.4"`).
  Assert the response is 403 and the body contains `"Access denied"`.

For the blocked IP test, use the `environ_base` parameter of the test client:
```python
response = client.get("/health", environ_base={"REMOTE_ADDR": "1.2.3.4"})
assert response.status_code == 403
```

---

## Validation

Run the new tests:
```bash
python -m pytest tests/test_security.py -v -k "TestSaveCreds or TestChangePassword or TestVerify or TestCheckAuth or TestRequiresAuth or TestIpAllowlist" --cov=src/security --cov-report=term-missing
```

All tests must pass. Then run the full suite:
```bash
python -m pytest tests/ -q --tb=short 2>&1 | tail -10
```
Report the final coverage percentage for `src/security.py`.
```
