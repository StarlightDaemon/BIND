"""Shared pytest fixtures for BIND tests."""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Must be set before rss_server is imported so MagnetStore initialises against
# a valid path on a WAL-compatible filesystem (/tmp, not /mnt/e/).
_db_fd, _MODULE_DB_PATH = tempfile.mkstemp(suffix=".db", prefix="bind_test_module_")
os.close(_db_fd)
os.remove(_MODULE_DB_PATH)  # MagnetStore creates it fresh

os.environ.setdefault("BIND_DB_PATH", _MODULE_DB_PATH)
os.environ.setdefault("FLASK_SECRET_KEY", "testsecret")
os.environ.setdefault("BIND_AUTH_ENABLED", "false")


@pytest.fixture
def fresh_store(tmp_path):
    """Fresh, empty MagnetStore in a temp directory per test."""
    from src.core.storage import MagnetStore
    return MagnetStore(str(tmp_path / "test.db"))


@pytest.fixture
def sample_html():
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
    from src.rss_server import app
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(flask_app, fresh_store, monkeypatch):
    """Flask test client with a fresh, empty store injected."""
    monkeypatch.setattr("src.rss_server.store", fresh_store)
    return flask_app.test_client()


@pytest.fixture(autouse=True)
def mock_setup_complete(monkeypatch):
    monkeypatch.setattr("src.rss_server.is_setup_complete", lambda: True)
