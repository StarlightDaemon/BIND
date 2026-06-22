"""
Auth-enforcement matrix test (TEST-1).

Verifies that every session-protected /api/ route:
  - Returns 401 when auth is enabled and no session is present.
  - Returns something other than 401 (guard passed) when an authenticated
    session is present.

A meta-assertion checks that PROTECTED_ROUTES covers every /api/ rule that
is not in the explicit PUBLIC_API_ROUTES allowlist, so adding a new route
without updating this file causes a loud failure.
"""

import pytest

# ---------------------------------------------------------------------------
# Route catalogue
# ---------------------------------------------------------------------------

# (method, path, needs_json_body)
# needs_json_body=True means a minimal JSON payload is required so the route
# body-parsing doesn't short-circuit before the auth guard fires.
PROTECTED_ROUTES: list[tuple[str, str, bool]] = [
    ("GET", "/api/stats", False),
    ("GET", "/api/metrics", False),
    ("GET", "/api/settings", False),
    ("POST", "/api/settings", True),
    ("POST", "/api/scraping/enable", False),
    ("POST", "/api/settings/trackers", True),
    ("POST", "/api/settings/password", True),
    ("GET", "/api/logs", False),
    ("POST", "/api/trigger-scrape", False),
    ("GET", "/api/magnets", False),
]

# Routes that are intentionally public (no session required).
PUBLIC_API_ROUTES: set[str] = {
    "/api/login",
    "/api/logout",
    "/api/me",
    "/api/csrf-token",
    "/api/setup",
    "/api/setup/status",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _set_csrf(client, token: str = "test-csrf-token") -> None:
    """Inject a CSRF token into the session so JSON-CSRF validation passes."""
    with client.session_transaction() as sess:
        sess["csrf_token"] = token


def _make_request(
    client, method: str, path: str, needs_json_body: bool, token: str = "test-csrf-token"
):
    """Issue a request with the CSRF header set."""
    headers = {"X-CSRF-Token": token}
    if method == "GET":
        return client.get(path, headers=headers)
    # POST
    if needs_json_body:
        return client.post(path, json={}, headers=headers)
    return client.post(path, headers=headers)


# ---------------------------------------------------------------------------
# Parametrized: 401 when auth is enabled and no session
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("method,path,needs_json_body", PROTECTED_ROUTES)
def test_returns_401_when_unauthenticated(method, path, needs_json_body, client, set_live_flag):
    """Each protected route must return 401 with auth enabled and no session."""
    set_live_flag("BIND_AUTH_ENABLED", "true")
    _set_csrf(client)
    resp = _make_request(client, method, path, needs_json_body)
    assert resp.status_code == 401, (
        f"{method} {path} returned {resp.status_code} — expected 401 (unauthenticated)"
    )


# ---------------------------------------------------------------------------
# Parametrized: not 401 when session is authenticated
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("method,path,needs_json_body", PROTECTED_ROUTES)
def test_auth_guard_passes_when_authenticated(method, path, needs_json_body, client, set_live_flag):
    """Each protected route must not return 401 when auth is enabled + session authenticated."""
    set_live_flag("BIND_AUTH_ENABLED", "true")
    with client.session_transaction() as sess:
        sess["csrf_token"] = "test-csrf-token"
        sess["authenticated"] = True
    resp = _make_request(client, method, path, needs_json_body)
    assert resp.status_code != 401, (
        f"{method} {path} returned 401 even with an authenticated session"
    )


# ---------------------------------------------------------------------------
# Meta-assertion: PROTECTED_ROUTES covers all non-public /api/ rules
# ---------------------------------------------------------------------------


def test_protected_routes_covers_all_api_rules(flask_app):
    """
    Every /api/ rule that is not in PUBLIC_API_ROUTES must appear in
    PROTECTED_ROUTES.  This test fails loudly when a new route is added
    without being classified.
    """
    protected_paths = {path for _, path, _ in PROTECTED_ROUTES}

    registered: set[str] = set()
    for rule in flask_app.url_map.iter_rules():
        path = str(rule)
        if path.startswith("/api/"):
            registered.add(path)

    unclassified = registered - PUBLIC_API_ROUTES - protected_paths
    assert not unclassified, (
        f"The following /api/ routes are neither in PUBLIC_API_ROUTES nor in "
        f"PROTECTED_ROUTES: {sorted(unclassified)}\n"
        "Add them to one of those lists in tests/test_auth_matrix.py."
    )
