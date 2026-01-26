"""Shared pytest fixtures for BIND tests."""

import os
import sys

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def temp_magnets_dir(tmp_path):
    """Create a temporary directory for magnet files."""
    magnets_dir = tmp_path / "magnets"
    magnets_dir.mkdir()
    return str(magnets_dir)


@pytest.fixture
def sample_html():
    """Sample HTML response mimicking AudioBookBay listing page."""
    return """
    <html>
    <body>
        <div class="post">
            <div class="postTitle">
                <a href="/audio-books/test-book-1/">Test Book 1</a>
            </div>
        </div>
        <div class="post">
            <div class="postTitle">
                <a href="/audio-books/test-book-2/">Test Book 2</a>
            </div>
        </div>
    </body>
    </html>
    """


@pytest.fixture
def sample_detail_html():
    """Sample detail page with info hash."""
    return """
    <html>
    <body>
        <div class="postContent">
            <table>
                <tr><td>Info Hash:</td><td>abc123def456789012345678901234567890abcd</td></tr>
            </table>
        </div>
    </body>
    </html>
    """


@pytest.fixture
def flask_app():
    """Create Flask test application."""
    from src.rss_server import app

    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(flask_app):
    """Flask test client."""
    return flask_app.test_client()


@pytest.fixture(autouse=True)
def mock_setup_complete(monkeypatch):
    """Bypass setup check by default for all tests."""
    # Patch the function where it is used in rss_server
    monkeypatch.setattr("src.rss_server.is_setup_complete", lambda: True)
