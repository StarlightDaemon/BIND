from unittest.mock import patch

import pytest
from src.rss_server import app


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@patch('src.rss_server.check_daemon_status')
@patch('src.rss_server.read_magnets')
def test_api_stats(mock_read_magnets, mock_check_daemon, client):
    # Setup mocks
    mock_check_daemon.return_value = ("online", "Active (Last job: 5m ago)", 1234567890)
    mock_read_magnets.return_value = [{"magnet": "test"}] * 42  # 42 magnets

    # Call API
    response = client.get('/api/stats')
    data = response.get_json()

    # Verify
    assert response.status_code == 200
    assert data['system_status'] == "online"
    assert data['status_message'] == "Active (Last job: 5m ago)"
    assert data['magnet_count'] == 42
    assert 'server_time' in data

@patch('src.rss_server.check_daemon_status')
@patch('src.rss_server.read_magnets')
def test_api_stats_offline(mock_read_magnets, mock_check_daemon, client):
    # Setup mocks
    mock_check_daemon.return_value = ("offline", "Stalled", 0)
    mock_read_magnets.return_value = []

    # Call API
    response = client.get('/api/stats')
    data = response.get_json()

    # Verify
    assert response.status_code == 200
    assert data['system_status'] == "offline"
    assert data['magnet_count'] == 0
