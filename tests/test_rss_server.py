"""Integration tests for RSS server Flask routes."""


class TestHealthEndpoint:
    """Test suite for /health endpoint."""

    def test_health_returns_200(self, client):
        """Health check should return 200 OK."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_json(self, client):
        """Health check should return JSON response."""
        response = client.get("/health")
        data = response.get_json()
        assert data is not None
        assert "status" in data


class TestFeedEndpoint:
    """Test suite for /feed.xml RSS endpoint."""

    def test_feed_returns_200(self, client):
        """Feed endpoint should return 200 OK."""
        response = client.get("/feed.xml")
        assert response.status_code == 200

    def test_feed_returns_xml_content_type(self, client):
        """Feed should have XML content type."""
        response = client.get("/feed.xml")
        assert "xml" in response.content_type.lower()

    def test_feed_has_rss_structure(self, client):
        """Feed should have valid RSS 2.0 structure."""
        response = client.get("/feed.xml")

        assert b"<rss" in response.data
        assert b'version="2.0"' in response.data
        assert b"<channel>" in response.data
        assert b"</channel>" in response.data

    def test_feed_has_title(self, client):
        """Feed should include title element."""
        response = client.get("/feed.xml")
        assert b"<title>" in response.data


class TestIndexEndpoint:
    """Test suite for / web UI endpoint."""

    def test_index_returns_200(self, client):
        """Index page should return 200 OK."""
        response = client.get("/")
        assert response.status_code == 200

    def test_index_returns_html(self, client):
        """Index should return HTML content type."""
        response = client.get("/")
        assert "text/html" in response.content_type

    def test_index_contains_branding(self, client):
        """Index page should contain BIND branding."""
        response = client.get("/")
        assert b"BIND" in response.data

    def test_index_has_html_structure(self, client):
        """Index should have valid HTML structure."""
        response = client.get("/")
        assert b"<!DOCTYPE html>" in response.data or b"<html" in response.data
        assert b"</html>" in response.data


class TestNotFoundHandling:
    """Test 404 handling for unknown routes."""

    def test_unknown_route_returns_404(self, client):
        """Unknown routes should return 404."""
        response = client.get("/nonexistent-page")
        assert response.status_code == 404
