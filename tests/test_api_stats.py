from unittest.mock import patch

HASH_A = "a" * 40


def test_api_stats_returns_true_count(client, fresh_store):
    for i in range(42):
        fresh_store.add_magnet("a" * 39 + str(i), f"Book {i}", "2024-01-01")

    with (
        patch("src.rss_server.check_daemon_status", return_value=("online", "Active (Last job: 5m ago)", 1234567890)),
        patch("src.security.check_auth", return_value=True),
    ):
        response = client.get("/api/stats")

    data = response.get_json()
    assert response.status_code == 200
    assert data["system_status"] == "online"
    assert data["status_message"] == "Active (Last job: 5m ago)"
    assert data["magnet_count"] == 42
    assert "server_time" in data


def test_api_stats_offline(client, fresh_store):
    with (
        patch("src.rss_server.check_daemon_status", return_value=("offline", "Stalled", 0)),
        patch("src.security.check_auth", return_value=True),
    ):
        response = client.get("/api/stats")

    data = response.get_json()
    assert response.status_code == 200
    assert data["system_status"] == "offline"
    assert data["magnet_count"] == 0


def test_api_stats_count_not_capped_at_100(client, fresh_store):
    for i in range(110):
        fresh_store.add_magnet("a" * 39 + str(i), f"Book {i}", "2024-01-01")

    with (
        patch("src.rss_server.check_daemon_status", return_value=("online", "ok", 0)),
        patch("src.security.check_auth", return_value=True),
    ):
        response = client.get("/api/stats")

    assert response.get_json()["magnet_count"] == 110
