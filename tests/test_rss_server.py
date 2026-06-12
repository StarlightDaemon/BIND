"""Integration tests for RSS server Flask routes."""

import os
import pathlib

from src.rss_server import _date_to_rfc2822, _resolve_secret_key

HASH_A = "a" * 40
HASH_B = "b" * 40


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_json(self, client):
        data = client.get("/health").get_json()
        assert data is not None
        assert "status" in data
        assert data["status"] == "ok"

    def test_health_returns_magnet_count(self, client, fresh_store):
        fresh_store.add_magnet(HASH_A, "Test Book", "2024-01-01")
        data = client.get("/health").get_json()
        assert data["magnet_count"] == 1

    def test_health_count_not_capped(self, client, fresh_store):
        for i in range(110):
            fresh_store.add_magnet("a" * 39 + str(i), f"Book {i}", "2024-01-01")
        data = client.get("/health").get_json()
        assert data["magnet_count"] == 110

    def test_health_does_not_leak_db_path(self, client):
        data = client.get("/health").get_json()
        assert "db_path" not in data


class TestSecurityHeaders:
    def test_x_content_type_options_present(self, client):
        resp = client.get("/health")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options_present(self, client):
        resp = client.get("/health")
        assert resp.headers.get("X-Frame-Options") == "DENY"

    def test_referrer_policy_present(self, client):
        resp = client.get("/health")
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_security_headers_on_feed(self, client):
        resp = client.get("/feed.xml")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"


class TestFeedEndpoint:
    def test_feed_returns_200(self, client):
        assert client.get("/feed.xml").status_code == 200

    def test_feed_returns_xml_content_type(self, client):
        assert "xml" in client.get("/feed.xml").content_type.lower()

    def test_feed_has_rss_structure(self, client):
        data = client.get("/feed.xml").data
        assert b"<rss" in data
        assert b'version="2.0"' in data
        assert b"<channel>" in data

    def test_feed_includes_magnet_items(self, client, fresh_store):
        fresh_store.add_magnet(HASH_A, "Great Audiobook", "2024-01-01")
        data = client.get("/feed.xml").data
        assert b"Great Audiobook" in data
        assert b"magnet:" in data

    def test_feed_empty_store(self, client):
        data = client.get("/feed.xml").data
        assert b"<item>" not in data


class TestIndexEndpoint:
    def test_index_returns_200(self, client):
        assert client.get("/api/dashboard").status_code == 200

    def test_index_returns_json(self, client):
        assert client.get("/api/dashboard").is_json

    def test_index_contains_expected_keys(self, client):
        data = client.get("/api/dashboard").get_json()
        assert "magnet_count" in data
        assert "magnets" in data
        assert "system_status" in data

    def test_index_shows_magnets(self, client, fresh_store):
        fresh_store.add_magnet(HASH_A, "My Audiobook Title", "2024-01-01")
        data = client.get("/api/dashboard").get_json()
        titles = [m["title"] for m in data["magnets"]]
        assert "My Audiobook Title" in titles


class TestMagnetsEndpoint:
    def test_magnets_returns_200(self, client):
        assert client.get("/api/magnets").status_code == 200

    def test_magnets_search_returns_matching(self, client, fresh_store):
        fresh_store.add_magnet(HASH_A, "John Doe Story", "2024-01-01")
        fresh_store.add_magnet(HASH_B, "Jane Smith Story", "2024-01-01")
        data = client.get("/api/magnets?q=John").get_json()
        titles = [m["title"] for m in data["magnets"]]
        assert "John Doe Story" in titles
        assert "Jane Smith Story" not in titles

    def test_magnets_no_query_shows_all(self, client, fresh_store):
        fresh_store.add_magnet(HASH_A, "Book One", "2024-01-01")
        fresh_store.add_magnet(HASH_B, "Book Two", "2024-01-01")
        data = client.get("/api/magnets").get_json()
        titles = [m["title"] for m in data["magnets"]]
        assert "Book One" in titles
        assert "Book Two" in titles


class TestNotFoundHandling:
    def test_unknown_route_serves_spa(self, client):
        # SPA catch-all handles all unmatched routes; 503 when frontend dist not built
        response = client.get("/nonexistent-page")
        assert response.status_code in (200, 503)


class TestResolveSecretKey:
    def test_env_var_takes_priority(self, tmp_path, monkeypatch):
        monkeypatch.setenv("FLASK_SECRET_KEY", "explicit-key")
        assert _resolve_secret_key(str(tmp_path)) == "explicit-key"

    def test_auto_generates_when_unset(self, tmp_path, monkeypatch):
        monkeypatch.delenv("FLASK_SECRET_KEY", raising=False)
        key = _resolve_secret_key(str(tmp_path))
        assert len(key) == 64  # 32 bytes hex
        assert key.isalnum()

    def test_persists_generated_key(self, tmp_path, monkeypatch):
        monkeypatch.delenv("FLASK_SECRET_KEY", raising=False)
        key1 = _resolve_secret_key(str(tmp_path))
        key2 = _resolve_secret_key(str(tmp_path))
        assert key1 == key2

    def test_key_file_has_restricted_permissions(self, tmp_path, monkeypatch):
        monkeypatch.delenv("FLASK_SECRET_KEY", raising=False)
        _resolve_secret_key(str(tmp_path))
        key_file = tmp_path / ".secret_key"
        assert oct(key_file.stat().st_mode)[-3:] == "600"

    def test_ephemeral_fallback_when_unwritable(self, tmp_path, monkeypatch):
        monkeypatch.delenv("FLASK_SECRET_KEY", raising=False)
        unwritable = tmp_path / "nope"
        unwritable.mkdir()
        unwritable.chmod(0o000)
        try:
            key = _resolve_secret_key(str(unwritable / "sub"))
            assert len(key) == 64
        finally:
            unwritable.chmod(0o755)


class TestDateToRfc2822:
    def test_valid_date(self):
        result = _date_to_rfc2822("2024-01-15")
        assert "2024" in result
        assert "Jan" in result

    def test_invalid_date_returns_current(self):
        result = _date_to_rfc2822("not-a-date")
        assert result  # just check it returns something non-empty


class TestMagnetsEdgeCases:
    def test_magnets_invalid_page_defaults_to_1(self, client):
        response = client.get("/api/magnets?page=abc")
        assert response.status_code == 200
        assert response.get_json()["page"] == 1


class TestSettingsRoute:
    def test_settings_get_returns_200(self, client):
        response = client.get("/api/settings")
        assert response.status_code == 200
        assert response.is_json

    def test_settings_post_save_success_and_restart_success(self, client, monkeypatch):
        monkeypatch.setattr("src.rss_server.config_manager.write_config", lambda cfg: (True, ""))
        monkeypatch.setattr("src.rss_server.config_manager.restart_daemon", lambda: (True, ""))
        with client.session_transaction() as sess:
            sess["csrf_token"] = "test-token"
        response = client.post(
            "/api/settings",
            json={"ABB_URL": "http://test"},
            headers={"X-CSRF-Token": "test-token"},
        )
        assert response.status_code == 200
        assert "restarted successfully" in response.get_json()["message"]

    def test_settings_post_save_success_but_restart_fails(self, client, monkeypatch):
        monkeypatch.setattr("src.rss_server.config_manager.write_config", lambda cfg: (True, ""))
        monkeypatch.setattr(
            "src.rss_server.config_manager.restart_daemon", lambda: (False, "restart err")
        )
        with client.session_transaction() as sess:
            sess["csrf_token"] = "test-token"
        response = client.post(
            "/api/settings",
            json={"ABB_URL": "http://test"},
            headers={"X-CSRF-Token": "test-token"},
        )
        assert response.status_code == 200
        assert "restart err" in response.get_json()["message"]

    def test_settings_post_write_fails(self, client, monkeypatch):
        monkeypatch.setattr(
            "src.rss_server.config_manager.write_config", lambda cfg: (False, "write err")
        )
        with client.session_transaction() as sess:
            sess["csrf_token"] = "test-token"
        response = client.post(
            "/api/settings",
            json={"ABB_URL": "http://test"},
            headers={"X-CSRF-Token": "test-token"},
        )
        assert response.status_code == 400
        assert "write err" in response.get_json()["message"]


class TestSettingsTrackersRoute:
    def test_settings_trackers_post_success(self, client, monkeypatch):
        def mock_set(text):
            pass

        monkeypatch.setattr("src.rss_server.tracker_manager.set_trackers_from_text", mock_set)
        with client.session_transaction() as sess:
            sess["csrf_token"] = "test-token"
        response = client.post(
            "/api/settings/trackers",
            json={"trackers": "udp://test"},
            headers={"X-CSRF-Token": "test-token"},
        )
        assert response.status_code == 200
        assert response.get_json()["message"] == "Trackers updated successfully."

    def test_settings_trackers_post_exception(self, client, monkeypatch):
        def mock_set(text):
            raise ValueError("bad trackers")

        monkeypatch.setattr("src.rss_server.tracker_manager.set_trackers_from_text", mock_set)
        with client.session_transaction() as sess:
            sess["csrf_token"] = "test-token"
        response = client.post(
            "/api/settings/trackers",
            json={"trackers": "udp://test"},
            headers={"X-CSRF-Token": "test-token"},
        )
        assert response.status_code == 400
        assert "bad trackers" in response.get_json()["message"]


class TestLogsRoute:
    def test_logs_security_log_exists(self, client, monkeypatch, tmp_path):
        log_file = tmp_path / "security.log"
        log_file.write_text("sec log content")
        monkeypatch.setattr("src.rss_server.get_security_log_path", lambda: str(log_file))
        response = client.get("/api/logs?log=security")
        assert response.status_code == 200
        data = response.get_json()
        assert "sec log content" in data["logs"]

    def test_logs_security_log_missing(self, client, monkeypatch, tmp_path):
        missing_file = tmp_path / "missing.log"
        monkeypatch.setattr("src.rss_server.get_security_log_path", lambda: str(missing_file))
        response = client.get("/api/logs?log=security")
        assert response.status_code == 200
        data = response.get_json()
        assert any("Log file not found:" in line for line in data["logs"])

    def test_logs_daemon_log_type(self, client, monkeypatch, tmp_path):
        monkeypatch.setattr("src.rss_server.get_logs_dir", lambda: str(tmp_path))
        log_file = tmp_path / "bind.log"
        log_file.write_text("daemon log content")
        response = client.get("/api/logs?log=daemon")
        assert response.status_code == 200
        data = response.get_json()
        assert "daemon log content" in data["logs"]


class TestChangePasswordRoute:
    def test_change_password_mismatch(self, client):
        with client.session_transaction() as sess:
            sess["csrf_token"] = "test-token"
        response = client.post(
            "/api/settings/password",
            json={"current_password": "old", "new_password": "new", "confirm_new_password": "diff"},
            headers={"X-CSRF-Token": "test-token"},
        )
        assert response.status_code == 400
        assert "do not match" in response.get_json()["message"]

    def test_change_password_success(self, client, monkeypatch):
        monkeypatch.setattr(
            "src.rss_server.change_password", lambda old, new, ip="": (True, "Password changed.")
        )
        with client.session_transaction() as sess:
            sess["csrf_token"] = "test-token"
        response = client.post(
            "/api/settings/password",
            json={"current_password": "old", "new_password": "new", "confirm_new_password": "new"},
            headers={"X-CSRF-Token": "test-token"},
        )
        assert response.status_code == 200
        assert "Password changed." in response.get_json()["message"]

    def test_change_password_current_incorrect(self, client, monkeypatch):
        monkeypatch.setattr(
            "src.rss_server.change_password", lambda old, new, ip="": (False, "Wrong password.")
        )
        with client.session_transaction() as sess:
            sess["csrf_token"] = "test-token"
        response = client.post(
            "/api/settings/password",
            json={
                "current_password": "wrong",
                "new_password": "new",
                "confirm_new_password": "new",
            },
            headers={"X-CSRF-Token": "test-token"},
        )
        assert response.status_code == 400
        assert "Wrong password." in response.get_json()["message"]


class TestCheckDaemonStatus:
    def test_status_online(self, monkeypatch, tmp_path):
        from src.rss_server import check_daemon_status

        monkeypatch.setattr("src.rss_server.get_logs_dir", lambda: str(tmp_path))
        monkeypatch.setattr(
            "src.rss_server.config_manager.read_config", lambda: {"SCRAPE_INTERVAL": "60"}
        )
        log_path = tmp_path / "bind.log"
        log_path.touch()
        status, msg, mtime = check_daemon_status()
        assert status == "online"
        assert "Active" in msg

    def test_status_offline(self, monkeypatch, tmp_path):
        import os
        import time

        from src.rss_server import check_daemon_status

        monkeypatch.setattr("src.rss_server.get_logs_dir", lambda: str(tmp_path))
        monkeypatch.setattr(
            "src.rss_server.config_manager.read_config", lambda: {"SCRAPE_INTERVAL": "60"}
        )
        log_path = tmp_path / "bind.log"
        log_path.touch()
        os.utime(log_path, (time.time() - 3 * 3600, time.time() - 3 * 3600))
        status, msg, mtime = check_daemon_status()
        assert status == "offline"
        assert "Stalled" in msg

    def test_status_unknown_no_log_file(self, monkeypatch, tmp_path):
        from src.rss_server import check_daemon_status

        monkeypatch.setattr("src.rss_server.get_logs_dir", lambda: str(tmp_path))
        monkeypatch.setattr(
            "src.rss_server.config_manager.read_config", lambda: {"SCRAPE_INTERVAL": "60"}
        )
        status, msg, mtime = check_daemon_status()
        assert status == "unknown"
        assert "Log file not found" in msg

    def test_status_unknown_on_exception(self, monkeypatch):
        from src.rss_server import check_daemon_status

        monkeypatch.setattr(
            "src.rss_server.config_manager.read_config", lambda: {"SCRAPE_INTERVAL": "not-an-int"}
        )
        status, msg, mtime = check_daemon_status()
        assert status == "unknown"
        assert "Error checking status" in msg


class TestMetricsRoute:
    def test_metrics_returns_200(self, client, fresh_store):
        response = client.get("/api/metrics")
        assert response.status_code == 200
        assert response.is_json

    def test_metrics_shows_run_data(self, client, fresh_store):
        fresh_store.record_scrape_run(result="success", items_new=5, duration_s=2.5)
        data = client.get("/api/metrics").get_json()
        assert any(r["result"] == "success" for r in data["runs"])


class TestApiStatsRoute:
    def test_api_stats_returns_json(self, client, monkeypatch):
        monkeypatch.setattr("src.rss_server.check_daemon_status", lambda: ("online", "active", 1.0))
        response = client.get("/api/stats")
        assert response.status_code == 200
        assert response.is_json

    def test_api_stats_has_expected_keys(self, client, monkeypatch):
        monkeypatch.setattr("src.rss_server.check_daemon_status", lambda: ("online", "active", 1.0))
        data = client.get("/api/stats").get_json()
        assert "system_status" in data
        assert "status_message" in data
        assert "magnet_count" in data
        assert "recent_magnets" in data
        assert "server_time" in data


class TestCsrfTokenGeneration:
    def test_csrf_token_set_in_session_on_get(self, client, monkeypatch):
        client.get("/api/csrf-token")
        with client.session_transaction() as sess:
            assert "csrf_token" in sess
            assert sess["csrf_token"]

    def test_csrf_token_is_stable_across_requests(self, client, monkeypatch):
        client.get("/api/csrf-token")
        with client.session_transaction() as sess:
            token1 = sess["csrf_token"]
        client.get("/api/csrf-token")
        with client.session_transaction() as sess:
            token2 = sess["csrf_token"]
        assert token1 == token2


class TestCsrfProtection:
    def test_post_without_csrf_token_returns_403(self, client):
        response = client.post("/setup", data={})
        assert response.status_code == 403

    def test_post_with_wrong_csrf_token_returns_403(self, client):
        client.get("/")  # generate a real token in the session
        response = client.post("/setup", data={"csrf_token": "badtoken"})
        assert response.status_code == 403


class TestSetupRedirect:
    def test_redirects_to_setup_when_not_configured(self, client, monkeypatch):
        monkeypatch.setattr("src.rss_server.is_setup_complete", lambda: False)
        response = client.get("/")
        assert response.status_code == 302
        assert "/setup" in response.headers["Location"]

    def test_setup_status_complete(self, client):
        # autouse mock_setup_complete keeps is_setup_complete → True
        data = client.get("/api/setup/status").get_json()
        assert data["setup_complete"] is True


class TestSetupRoute:
    def test_api_setup_status_incomplete(self, client, monkeypatch):
        monkeypatch.setattr("src.rss_server.is_setup_complete", lambda: False)
        data = client.get("/api/setup/status").get_json()
        assert data["setup_complete"] is False

    def test_api_setup_post_password_mismatch(self, client, monkeypatch):
        monkeypatch.setattr("src.rss_server.is_setup_complete", lambda: False)
        with client.session_transaction() as sess:
            sess["csrf_token"] = "test-token"
        response = client.post(
            "/api/setup",
            json={"username": "admin", "password": "abc", "confirm_password": "xyz"},
            headers={"X-CSRF-Token": "test-token"},
        )
        assert response.status_code == 400
        assert "do not match" in response.get_json()["error"]

    def test_api_setup_post_success(self, client, monkeypatch):
        monkeypatch.setattr("src.rss_server.is_setup_complete", lambda: False)
        monkeypatch.setattr("src.rss_server.save_credentials", lambda u, p, ip="": (True, "ok"))
        written = {}
        monkeypatch.setattr(
            "src.rss_server.config_manager.write_config",
            lambda cfg: written.update(cfg) or (True, "ok"),
        )
        with client.session_transaction() as sess:
            sess["csrf_token"] = "test-token"
        response = client.post(
            "/api/setup",
            json={"username": "admin", "password": "secret", "confirm_password": "secret"},
            headers={"X-CSRF-Token": "test-token"},
        )
        assert response.status_code == 200
        assert response.get_json()["ok"] is True
        assert written.get("SCRAPING_ENABLED") == "false"


class TestTriggerScrapeRoute:
    def _post(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr("src.rss_server._data_dir", str(tmp_path))
        with client.session_transaction() as sess:
            sess["csrf_token"] = "test-token"
        return client.post(
            "/api/trigger-scrape",
            headers={"X-CSRF-Token": "test-token"},
        )

    def test_trigger_returns_200_and_ok(self, client, tmp_path, monkeypatch):
        resp = self._post(client, tmp_path, monkeypatch)
        assert resp.status_code == 200
        assert resp.get_json()["ok"] is True

    def test_trigger_writes_trigger_file(self, client, tmp_path, monkeypatch):
        self._post(client, tmp_path, monkeypatch)
        assert os.path.exists(str(tmp_path / ".trigger"))

    def test_trigger_409_when_file_already_exists(self, client, tmp_path, monkeypatch):
        (tmp_path / ".trigger").touch()
        monkeypatch.setattr("src.rss_server._data_dir", str(tmp_path))
        with client.session_transaction() as sess:
            sess["csrf_token"] = "test-token"
        resp = client.post(
            "/api/trigger-scrape",
            headers={"X-CSRF-Token": "test-token"},
        )
        assert resp.status_code == 409
        assert resp.get_json()["ok"] is False

    def test_trigger_500_on_oserror(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr("src.rss_server._data_dir", str(tmp_path))

        def bad_touch(self, *args, **kwargs):
            raise OSError("disk full")

        monkeypatch.setattr("pathlib.Path.touch", bad_touch)
        with client.session_transaction() as sess:
            sess["csrf_token"] = "test-token"
        resp = client.post(
            "/api/trigger-scrape",
            headers={"X-CSRF-Token": "test-token"},
        )
        assert resp.status_code == 500
        assert "disk full" in resp.get_json()["message"]

    def test_trigger_401_when_auth_required_and_unauthenticated(
        self, client, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("BIND_AUTH_ENABLED", "true")
        monkeypatch.setattr("src.rss_server._data_dir", str(tmp_path))
        with client.session_transaction() as sess:
            sess["csrf_token"] = "test-token"
            sess.pop("authenticated", None)
        resp = client.post(
            "/api/trigger-scrape",
            headers={"X-CSRF-Token": "test-token"},
        )
        assert resp.status_code == 401


class TestLoginRoute:
    def _post(self, client, payload, token="test-token"):
        with client.session_transaction() as sess:
            sess["csrf_token"] = token
        return client.post("/api/login", json=payload, headers={"X-CSRF-Token": token})

    def test_valid_credentials_returns_ok(self, client, monkeypatch):
        monkeypatch.setattr("src.rss_server.verify_credentials", lambda u, p, ip="": True)
        resp = self._post(client, {"username": "admin", "password": "secret"})
        assert resp.status_code == 200
        assert resp.get_json()["ok"] is True

    def test_invalid_credentials_returns_401(self, client, monkeypatch):
        monkeypatch.setattr("src.rss_server.verify_credentials", lambda u, p, ip="": False)
        resp = self._post(client, {"username": "admin", "password": "wrong"})
        assert resp.status_code == 401
        assert "Invalid credentials" in resp.get_json()["error"]


class TestLogoutRoute:
    def test_logout_returns_ok(self, client):
        with client.session_transaction() as sess:
            sess["csrf_token"] = "test-token"
            sess["authenticated"] = True
        resp = client.post("/api/logout", headers={"X-CSRF-Token": "test-token"})
        assert resp.status_code == 200
        assert resp.get_json()["ok"] is True


class TestMeRoute:
    def test_me_auth_enabled_unauthenticated(self, client, monkeypatch):
        monkeypatch.setenv("BIND_AUTH_ENABLED", "true")
        resp = client.get("/api/me")
        data = resp.get_json()
        assert data["auth_enabled"] is True
        assert data["authenticated"] is False

    def test_me_auth_enabled_with_valid_session(self, client, monkeypatch):
        monkeypatch.setenv("BIND_AUTH_ENABLED", "true")
        with client.session_transaction() as sess:
            sess["authenticated"] = True
        resp = client.get("/api/me")
        data = resp.get_json()
        assert data["auth_enabled"] is True
        assert data["authenticated"] is True


class TestSessionAuthProceedsWhenAuthenticated:
    """Covers requires_session_auth line 224: auth enabled + authenticated session → proceed."""

    def test_authenticated_session_returns_200_when_auth_enabled(
        self, client, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("BIND_AUTH_ENABLED", "true")
        monkeypatch.setattr("src.rss_server._data_dir", str(tmp_path))
        with client.session_transaction() as sess:
            sess["csrf_token"] = "test-token"
            sess["authenticated"] = True
        resp = client.post("/api/trigger-scrape", headers={"X-CSRF-Token": "test-token"})
        assert resp.status_code == 200


class TestSetupRouteAdditional:
    def test_setup_already_complete_returns_400(self, client):
        # autouse mock_setup_complete keeps is_setup_complete → True
        with client.session_transaction() as sess:
            sess["csrf_token"] = "test-token"
        resp = client.post(
            "/api/setup",
            json={"username": "admin", "password": "pass", "confirm_password": "pass"},
            headers={"X-CSRF-Token": "test-token"},
        )
        assert resp.status_code == 400
        assert "already complete" in resp.get_json()["error"]

    def test_setup_save_credentials_failure_returns_400(self, client, monkeypatch):
        monkeypatch.setattr("src.rss_server.is_setup_complete", lambda: False)
        monkeypatch.setattr(
            "src.rss_server.save_credentials",
            lambda u, p, ip="": (False, "Username too short"),
        )
        with client.session_transaction() as sess:
            sess["csrf_token"] = "test-token"
        resp = client.post(
            "/api/setup",
            json={"username": "a", "password": "pass", "confirm_password": "pass"},
            headers={"X-CSRF-Token": "test-token"},
        )
        assert resp.status_code == 400
        assert "Username too short" in resp.get_json()["error"]

    def test_setup_write_config_failure_returns_500(self, client, monkeypatch):
        monkeypatch.setattr("src.rss_server.is_setup_complete", lambda: False)
        monkeypatch.setattr("src.rss_server.save_credentials", lambda u, p, ip="": (True, "ok"))
        monkeypatch.setattr(
            "src.rss_server.config_manager.write_config",
            lambda cfg: (False, "disk full"),
        )
        with client.session_transaction() as sess:
            sess["csrf_token"] = "test-token"
        resp = client.post(
            "/api/setup",
            json={"username": "admin", "password": "pass", "confirm_password": "pass"},
            headers={"X-CSRF-Token": "test-token"},
        )
        assert resp.status_code == 500
        assert "disk full" in resp.get_json()["error"]


class TestScrapingEnableRoute:
    def _post(self, client):
        with client.session_transaction() as sess:
            sess["csrf_token"] = "test-token"
        return client.post("/api/scraping/enable", headers={"X-CSRF-Token": "test-token"})

    def test_already_enabled_returns_ok(self, client, monkeypatch):
        monkeypatch.setattr(
            "src.rss_server.config_manager.read_config",
            lambda: {"SCRAPING_ENABLED": "true"},
        )
        resp = self._post(client)
        assert resp.status_code == 200
        assert "already enabled" in resp.get_json()["message"]

    def test_write_failure_returns_400(self, client, monkeypatch):
        monkeypatch.setattr(
            "src.rss_server.config_manager.read_config",
            lambda: {"SCRAPING_ENABLED": "false"},
        )
        monkeypatch.setattr(
            "src.rss_server.config_manager.write_config",
            lambda cfg: (False, "write error"),
        )
        resp = self._post(client)
        assert resp.status_code == 400
        assert resp.get_json()["ok"] is False

    def test_sentinel_oserror_is_swallowed(self, client, monkeypatch, tmp_path):
        monkeypatch.setattr(
            "src.rss_server.config_manager.read_config",
            lambda: {"SCRAPING_ENABLED": "false"},
        )
        monkeypatch.setattr(
            "src.rss_server.config_manager.write_config",
            lambda cfg: (True, "ok"),
        )
        monkeypatch.setattr("src.rss_server.get_data_dir", lambda: str(tmp_path))
        monkeypatch.setattr(
            "src.rss_server.config_manager.restart_daemon", lambda: (False, "no systemd")
        )

        def raise_oserror(self, *args, **kwargs):
            raise OSError("read-only filesystem")

        monkeypatch.setattr(pathlib.Path, "touch", raise_oserror)
        resp = self._post(client)
        assert resp.status_code == 200
        assert resp.get_json()["ok"] is True

    def test_daemon_restart_success_message(self, client, monkeypatch, tmp_path):
        monkeypatch.setattr(
            "src.rss_server.config_manager.read_config",
            lambda: {"SCRAPING_ENABLED": "false"},
        )
        monkeypatch.setattr(
            "src.rss_server.config_manager.write_config",
            lambda cfg: (True, "ok"),
        )
        monkeypatch.setattr("src.rss_server.get_data_dir", lambda: str(tmp_path))
        monkeypatch.setattr(
            "src.rss_server.config_manager.restart_daemon", lambda: (True, "restarted")
        )
        resp = self._post(client)
        assert resp.status_code == 200
        assert "Daemon restarted" in resp.get_json()["message"]


class TestLogsReadError:
    def test_logs_read_exception_returns_error_entry(self, client, monkeypatch, tmp_path):
        log_file = tmp_path / "security.log"
        log_file.write_text("data")
        monkeypatch.setattr("src.rss_server.get_security_log_path", lambda: str(log_file))

        real_open = open

        def bad_open(path, *args, **kwargs):
            if str(log_file) == str(path):
                raise OSError("permission denied")
            return real_open(path, *args, **kwargs)

        monkeypatch.setattr("builtins.open", bad_open)
        resp = client.get("/api/logs?log=security")
        assert resp.status_code == 200
        assert any("Error reading log file" in line for line in resp.get_json()["logs"])


class TestSpaFallback:
    def test_returns_503_when_frontend_not_built(self, client, monkeypatch):
        from src.rss_server import _SPA_DIST

        spa_html = os.path.join(_SPA_DIST, "index.html")
        original_isfile = os.path.isfile

        def mock_isfile(path):
            if path == spa_html:
                return False
            return original_isfile(path)

        monkeypatch.setattr(os.path, "isfile", mock_isfile)
        resp = client.get("/some-spa-page")
        assert resp.status_code == 503
        assert b"Frontend not built" in resp.data


class TestCsrfJsonRejection:
    def test_api_post_without_csrf_header_returns_403(self, client):
        resp = client.post("/api/login", json={"username": "x", "password": "y"})
        assert resp.status_code == 403

    def test_api_post_with_wrong_csrf_header_returns_403(self, client):
        with client.session_transaction() as sess:
            sess["csrf_token"] = "real-token"
        resp = client.post(
            "/api/login",
            json={"username": "x", "password": "y"},
            headers={"X-CSRF-Token": "wrong-token"},
        )
        assert resp.status_code == 403


class TestCsrfFormValidToken:
    def test_form_post_with_valid_csrf_passes_validation(self, client):
        # Covers _validate_csrf_form 171->exit: condition is False (token matches)
        with client.session_transaction() as sess:
            sess["csrf_token"] = "valid-token"
        resp = client.post("/some-page", data={"csrf_token": "valid-token"})
        assert resp.status_code != 403
