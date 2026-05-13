"""Integration tests for RSS server Flask routes."""

import os

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
