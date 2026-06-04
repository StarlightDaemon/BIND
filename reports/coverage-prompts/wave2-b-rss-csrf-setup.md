# Group B — rss_server.py: CSRF + Setup Flow

**Model: Claude Sonnet**  
**Prereq: Run Group A first** (both append to `tests/test_rss_server.py`)  
**Working directory:** `/mnt/e/BIND`

## Why Claude for this group

These tests require understanding Flask session mechanics, how `before_request` hooks fire during testing, and the interaction between `is_setup_complete`, `csrf_protect`, and the client request context. The logic is subtle — get it wrong and the test passes for the wrong reason.

## Your task

Append new test classes to `tests/test_rss_server.py` covering CSRF protection,
the setup flow, and the `check_setup_required` redirect. Do NOT modify existing tests.

## Coverage targets

```
src/rss_server.py   Missing: 104-106, 110-114, 125, 132
```

- 104–106  → `generate_csrf_token()` — the branch where `csrf_token` is NOT yet in session (generates + stores it)
- 110–114  → `validate_csrf_token()` — POST with a missing or wrong token triggers `abort(403)`
- 125      → `check_setup_required()` — when `is_setup_complete()` returns False, redirects to `/setup`
- 132      → `csrf_protect()` — the POST path that calls `validate_csrf_token()`

The `/setup` GET + POST route (lines 368-388) may also be partially uncovered if Group A did not include it. Check after Group A runs.

## Key files to read before writing

- `src/rss_server.py` lines 98–135 (CSRF + before_request hooks)
- `src/rss_server.py` lines 366–388 (setup route)
- `tests/conftest.py` (fixtures)

## Critical facts

1. **Flask test client sessions:** Use `with client.session_transaction() as sess:` to inspect or pre-populate the session before a request. To test CSRF generation, make a GET request to any route and then check `session["csrf_token"]` was set.

2. **Testing CSRF rejection (403):** The `mock_setup_complete` autouse fixture returns True, so `check_setup_required` won't redirect. Make a POST to any route (e.g., `/settings`) with a deliberately wrong or missing `csrf_token` form field. Expect `status_code == 403`.

3. **Testing the setup redirect (line 125):** Override the autouse `mock_setup_complete` for a single test by using a local `monkeypatch.setattr("src.rss_server.is_setup_complete", lambda: False)`. Then GET `/` and assert it redirects to `/setup`.

4. **`/setup` GET when already complete:** With `is_setup_complete` returning True, GET `/setup` should redirect to `/`. Test this.

5. **`/setup` POST with password mismatch:** With `is_setup_complete` returning False, POST to `/setup` with `password != confirm_password`. Expect form re-renders with error (no redirect). Since CSRF runs for POST, you'll need to either patch `validate_csrf_token` or pre-populate the CSRF token in the session.

6. The simplest CSRF bypass for setup POST tests: `monkeypatch.setattr("src.rss_server.validate_csrf_token", lambda: None)`.

## Classes to write

```python
class TestCsrfTokenGeneration:
    # test_csrf_token_set_in_session_on_get
    #   GET any route, assert session["csrf_token"] is a non-empty string

    # test_csrf_token_is_stable_across_requests
    #   GET twice within same session, assert token is identical

class TestCsrfProtection:
    # test_post_without_csrf_token_returns_403
    #   POST to /settings with no csrf_token field

    # test_post_with_wrong_csrf_token_returns_403
    #   POST to /settings with mismatched csrf_token

class TestSetupRedirect:
    # test_redirects_to_setup_when_not_configured
    #   monkeypatch is_setup_complete → False, GET /, expect redirect to /setup

    # test_setup_already_done_redirects_to_index
    #   is_setup_complete → True (default), GET /setup, expect redirect to /

class TestSetupRoute:
    # test_setup_get_returns_200_when_not_configured
    #   monkeypatch is_setup_complete → False, GET /setup

    # test_setup_post_password_mismatch_shows_error
    #   is_setup_complete → False, POST with mismatched passwords

    # test_setup_post_success_redirects
    #   is_setup_complete → False, patch save_credentials → (True, "ok"),
    #   POST valid form, expect redirect to /
```

## Validation

After writing, run:
```bash
python -m pytest tests/test_rss_server.py -v --cov=src/rss_server --cov-report=term-missing
```
Confirm lines 104–106, 110–114, 125, 132 are no longer in the Missing column.
All tests must pass (no regressions from Group A).
