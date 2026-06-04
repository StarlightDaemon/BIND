"""Integration tests for RSS server Flask routes."""

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
        assert client.get("/").status_code == 200

    def test_index_returns_html(self, client):
        assert "text/html" in client.get("/").content_type

    def test_index_contains_branding(self, client):
        assert b"BIND" in client.get("/").data

    def test_index_shows_magnets(self, client, fresh_store):
        fresh_store.add_magnet(HASH_A, "My Audiobook Title", "2024-01-01")
        assert b"My Audiobook Title" in client.get("/").data


class TestMagnetsEndpoint:
    def test_magnets_returns_200(self, client):
        assert client.get("/magnets").status_code == 200

    def test_magnets_search_returns_matching(self, client, fresh_store):
        fresh_store.add_magnet(HASH_A, "John Doe Story", "2024-01-01")
        fresh_store.add_magnet(HASH_B, "Jane Smith Story", "2024-01-01")
        data = client.get("/magnets?q=John").data
        assert b"John Doe Story" in data
        assert b"Jane Smith Story" not in data

    def test_magnets_no_query_shows_all(self, client, fresh_store):
        fresh_store.add_magnet(HASH_A, "Book One", "2024-01-01")
        fresh_store.add_magnet(HASH_B, "Book Two", "2024-01-01")
        data = client.get("/magnets").data
        assert b"Book One" in data
        assert b"Book Two" in data


class TestNotFoundHandling:
    def test_unknown_route_returns_404(self, client):
        assert client.get("/nonexistent-page").status_code == 404


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
        response = client.get("/magnets?page=abc")
        assert response.status_code == 200

class TestSettingsRoute:
    def test_settings_get_returns_200(self, client):
        response = client.get("/settings")
        assert response.status_code == 200

    def test_settings_post_save_success_and_restart_success(self, client, monkeypatch):
        monkeypatch.setattr("src.rss_server.config_manager.write_config", lambda cfg: (True, ""))
        monkeypatch.setattr("src.rss_server.config_manager.restart_daemon", lambda: (True, ""))
        with client.session_transaction() as sess:
            sess["csrf_token"] = "test-token"
        response = client.post("/settings", data={"csrf_token": "test-token", "ABB_URL": "http://test"})
        assert response.status_code == 200
        assert b"Configuration saved. Daemon restarted successfully." in response.data

    def test_settings_post_save_success_but_restart_fails(self, client, monkeypatch):
        monkeypatch.setattr("src.rss_server.config_manager.write_config", lambda cfg: (True, ""))
        monkeypatch.setattr("src.rss_server.config_manager.restart_daemon", lambda: (False, "restart err"))
        with client.session_transaction() as sess:
            sess["csrf_token"] = "test-token"
        response = client.post("/settings", data={"csrf_token": "test-token", "ABB_URL": "http://test"})
        assert response.status_code == 200
        assert b"Configuration saved. Note: restart err" in response.data

    def test_settings_post_write_fails(self, client, monkeypatch):
        monkeypatch.setattr("src.rss_server.config_manager.write_config", lambda cfg: (False, "write err"))
        with client.session_transaction() as sess:
            sess["csrf_token"] = "test-token"
        response = client.post("/settings", data={"csrf_token": "test-token", "ABB_URL": "http://test"})
        assert response.status_code == 200
        assert b"write err" in response.data

class TestSettingsTrackersRoute:
    def test_settings_trackers_post_success(self, client, monkeypatch):
        def mock_set(text): pass
        monkeypatch.setattr("src.rss_server.tracker_manager.set_trackers_from_text", mock_set)
        with client.session_transaction() as sess:
            sess["csrf_token"] = "test-token"
        response = client.post("/settings/trackers", data={"csrf_token": "test-token", "trackers": "udp://test"})
        assert response.status_code == 200
        assert b"Trackers updated successfully." in response.data

    def test_settings_trackers_post_exception(self, client, monkeypatch):
        def mock_set(text): raise ValueError("bad trackers")
        monkeypatch.setattr("src.rss_server.tracker_manager.set_trackers_from_text", mock_set)
        with client.session_transaction() as sess:
            sess["csrf_token"] = "test-token"
        response = client.post("/settings/trackers", data={"csrf_token": "test-token", "trackers": "udp://test"})
        assert response.status_code == 200
        assert b"Failed to update trackers: bad trackers" in response.data

class TestLogsRoute:
    def test_logs_security_log_exists(self, client, monkeypatch, tmp_path):
        log_file = tmp_path / "security.log"
        log_file.write_text("sec log content")
        monkeypatch.setattr("src.rss_server.get_security_log_path", lambda: str(log_file))
        response = client.get("/logs?log=security")
        assert response.status_code == 200
        assert b"sec log content" in response.data

    def test_logs_security_log_missing(self, client, monkeypatch, tmp_path):
        missing_file = tmp_path / "missing.log"
        monkeypatch.setattr("src.rss_server.get_security_log_path", lambda: str(missing_file))
        response = client.get("/logs?log=security")
        assert response.status_code == 200
        assert b"Log file not found:" in response.data

    def test_logs_daemon_log_type(self, client, monkeypatch, tmp_path):
        monkeypatch.setattr("os.getcwd", lambda: str(tmp_path))
        log_file = tmp_path / "bind.log"
        log_file.write_text("daemon log content")
        response = client.get("/logs?log=daemon")
        assert response.status_code == 200
        assert b"daemon log content" in response.data

class TestChangePasswordRoute:
    def test_change_password_mismatch(self, client):
        with client.session_transaction() as sess:
            sess["csrf_token"] = "test-token"
        response = client.post("/settings/password", data={
            "csrf_token": "test-token",
            "current_password": "old",
            "new_password": "new",
            "confirm_new_password": "diff"
        })
        assert response.status_code == 200
        assert b"New passwords do not match." in response.data

    def test_change_password_success(self, client, monkeypatch):
        monkeypatch.setattr("src.rss_server.change_password", lambda old, new: (True, "Password changed."))
        with client.session_transaction() as sess:
            sess["csrf_token"] = "test-token"
        response = client.post("/settings/password", data={
            "csrf_token": "test-token",
            "current_password": "old",
            "new_password": "new",
            "confirm_new_password": "new"
        })
        assert response.status_code == 200
        assert b"Password changed." in response.data

    def test_change_password_current_incorrect(self, client, monkeypatch):
        monkeypatch.setattr("src.rss_server.change_password", lambda old, new: (False, "Wrong password."))
        with client.session_transaction() as sess:
            sess["csrf_token"] = "test-token"
        response = client.post("/settings/password", data={
            "csrf_token": "test-token",
            "current_password": "wrong",
            "new_password": "new",
            "confirm_new_password": "new"
        })
        assert response.status_code == 200
        assert b"Wrong password." in response.data

class TestCheckDaemonStatus:
    def test_status_online(self, monkeypatch, tmp_path):
        from src.rss_server import check_daemon_status
        monkeypatch.setattr("os.getcwd", lambda: str(tmp_path))
        monkeypatch.setattr("src.rss_server.config_manager.read_config", lambda: {"SCRAPE_INTERVAL": "60"})
        log_path = tmp_path / "bind.log"
        log_path.touch()
        status, msg, mtime = check_daemon_status()
        assert status == "online"
        assert "Active" in msg

    def test_status_offline(self, monkeypatch, tmp_path):
        import time
        import os
        from src.rss_server import check_daemon_status
        monkeypatch.setattr("os.getcwd", lambda: str(tmp_path))
        monkeypatch.setattr("src.rss_server.config_manager.read_config", lambda: {"SCRAPE_INTERVAL": "60"})
        log_path = tmp_path / "bind.log"
        log_path.touch()
        os.utime(log_path, (time.time() - 3 * 3600, time.time() - 3 * 3600))
        status, msg, mtime = check_daemon_status()
        assert status == "offline"
        assert "Stalled" in msg

    def test_status_unknown_no_log_file(self, monkeypatch, tmp_path):
        from src.rss_server import check_daemon_status
        monkeypatch.setattr("os.getcwd", lambda: str(tmp_path))
        monkeypatch.setattr("src.rss_server.config_manager.read_config", lambda: {"SCRAPE_INTERVAL": "60"})
        status, msg, mtime = check_daemon_status()
        assert status == "unknown"
        assert "Log file not found" in msg

    def test_status_unknown_on_exception(self, monkeypatch):
        from src.rss_server import check_daemon_status
        monkeypatch.setattr("src.rss_server.config_manager.read_config", lambda: {"SCRAPE_INTERVAL": "not-an-int"})
        status, msg, mtime = check_daemon_status()
        assert status == "unknown"
        assert "Error checking status" in msg

class TestMetricsRoute:
    def test_metrics_returns_200(self, client, fresh_store):
        response = client.get("/metrics")
        assert response.status_code == 200

    def test_metrics_shows_run_data(self, client, fresh_store):
        fresh_store.record_scrape_run(result="success", items_new=5, duration_s=2.5)
        response = client.get("/metrics")
        assert response.status_code == 200
        assert b"success" in response.data

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
        monkeypatch.setattr("src.rss_server.is_setup_complete", lambda: False)
        client.get("/setup")
        with client.session_transaction() as sess:
            assert "csrf_token" in sess
            assert sess["csrf_token"]

    def test_csrf_token_is_stable_across_requests(self, client, monkeypatch):
        monkeypatch.setattr("src.rss_server.is_setup_complete", lambda: False)
        client.get("/setup")
        with client.session_transaction() as sess:
            token1 = sess["csrf_token"]
        client.get("/setup")
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

    def test_setup_already_done_redirects_to_index(self, client):
        # autouse mock_setup_complete keeps is_setup_complete → True
        response = client.get("/setup")
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/")


class TestSetupRoute:
    def test_setup_get_returns_200_when_not_configured(self, client, monkeypatch):
        monkeypatch.setattr("src.rss_server.is_setup_complete", lambda: False)
        response = client.get("/setup")
        assert response.status_code == 200

    def test_setup_post_password_mismatch_shows_error(self, client, monkeypatch):
        monkeypatch.setattr("src.rss_server.is_setup_complete", lambda: False)
        monkeypatch.setattr("src.rss_server.validate_csrf_token", lambda: None)
        response = client.post(
            "/setup",
            data={"username": "admin", "password": "abc", "confirm_password": "xyz"},
        )
        assert response.status_code == 200
        assert b"Passwords do not match" in response.data

    def test_setup_post_success_redirects(self, client, monkeypatch):
        monkeypatch.setattr("src.rss_server.is_setup_complete", lambda: False)
        monkeypatch.setattr("src.rss_server.validate_csrf_token", lambda: None)
        monkeypatch.setattr(
            "src.rss_server.save_credentials", lambda u, p: (True, "ok")
        )
        response = client.post(
            "/setup",
            data={"username": "admin", "password": "secret", "confirm_password": "secret"},
        )
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/")
