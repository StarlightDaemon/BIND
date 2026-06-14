"""Wave 5-B: LiveConfig — precedence, live re-parse, and typed accessors."""

import os

from src.config_manager import ConfigManager, LiveConfig


def _write(path, **kv):
    path.write_text("".join(f"{k}={v}\n" for k, v in kv.items()))


class TestPrecedence:
    def test_default_when_no_file_and_no_env(self, tmp_path):
        cfg = LiveConfig(str(tmp_path / "config.env"), env={})
        assert cfg.get("SCRAPING_ENABLED") == ConfigManager.DEFAULTS["SCRAPING_ENABLED"]

    def test_file_value_beats_default(self, tmp_path):
        config_file = tmp_path / "config.env"
        _write(config_file, SCRAPING_ENABLED="false")
        cfg = LiveConfig(str(config_file), env={})
        assert cfg.get("SCRAPING_ENABLED") == "false"

    def test_process_start_env_beats_file(self, tmp_path):
        config_file = tmp_path / "config.env"
        _write(config_file, SCRAPING_ENABLED="false")
        cfg = LiveConfig(str(config_file), env={"SCRAPING_ENABLED": "true"})
        assert cfg.get("SCRAPING_ENABLED") == "true"

    def test_env_pinned_key_ignores_later_file_edits_permanently(self, tmp_path):
        """The operator contract: an exported env var wins for the process life."""
        config_file = tmp_path / "config.env"
        _write(config_file, BIND_AUTH_ENABLED="true")
        cfg = LiveConfig(str(config_file), env={"BIND_AUTH_ENABLED": "false"})
        assert cfg.get("BIND_AUTH_ENABLED") == "false"
        _write(config_file, BIND_AUTH_ENABLED="true", ABB_URL="http://x.example")
        assert cfg.get("BIND_AUTH_ENABLED") == "false"

    def test_env_changes_after_snapshot_are_ignored(self, tmp_path, monkeypatch):
        """Seeding-style mutation of os.environ after construction must not
        shadow the file — the exact bug class removed by Wave 5-B (SEC-2)."""
        config_file = tmp_path / "config.env"
        _write(config_file, BIND_AUTH_ENABLED="true")
        monkeypatch.delenv("BIND_AUTH_ENABLED", raising=False)
        cfg = LiveConfig(str(config_file))  # snapshot of real environ, key absent
        monkeypatch.setenv("BIND_AUTH_ENABLED", "false")
        assert cfg.get("BIND_AUTH_ENABLED") == "true"

    def test_only_managed_keys_are_snapshotted(self, tmp_path):
        cfg = LiveConfig(str(tmp_path / "config.env"), env={"PATH": "/bin", "ABB_URL": "http://a"})
        assert set(cfg.env_snapshot) == {"ABB_URL"}

    def test_unknown_key_returns_empty_string(self, tmp_path):
        cfg = LiveConfig(str(tmp_path / "config.env"), env={})
        assert cfg.get("NOT_A_MANAGED_KEY") == ""


class TestLiveReParse:
    def test_file_edit_is_picked_up_without_new_instance(self, tmp_path):
        config_file = tmp_path / "config.env"
        _write(config_file, SCRAPING_ENABLED="false")
        cfg = LiveConfig(str(config_file), env={})
        assert cfg.get_bool("SCRAPING_ENABLED") is False
        _write(config_file, SCRAPING_ENABLED="true", ABB_URL="http://b.example")
        assert cfg.get_bool("SCRAPING_ENABLED") is True
        assert cfg.get("ABB_URL") == "http://b.example"

    def test_file_deleted_falls_back_to_defaults(self, tmp_path):
        config_file = tmp_path / "config.env"
        _write(config_file, SCRAPING_ENABLED="false")
        cfg = LiveConfig(str(config_file), env={})
        assert cfg.get_bool("SCRAPING_ENABLED") is False
        os.remove(config_file)
        assert cfg.get_bool("SCRAPING_ENABLED") is True

    def test_unchanged_file_is_not_reparsed(self, tmp_path, monkeypatch):
        config_file = tmp_path / "config.env"
        _write(config_file, SCRAPING_ENABLED="false")
        cfg = LiveConfig(str(config_file), env={})
        cfg.get("SCRAPING_ENABLED")
        calls = {"n": 0}
        real_read = cfg._manager.read_config

        def counting_read():
            calls["n"] += 1
            return real_read()

        monkeypatch.setattr(cfg._manager, "read_config", counting_read)
        for _ in range(5):
            cfg.get("SCRAPING_ENABLED")
        assert calls["n"] == 0


class TestTypedAccessors:
    def test_get_bool_semantics(self, tmp_path):
        config_file = tmp_path / "config.env"
        _write(config_file, BIND_AUTH_ENABLED="FALSE")
        cfg = LiveConfig(str(config_file), env={})
        assert cfg.get_bool("BIND_AUTH_ENABLED") is False
        # Anything but "false" is true (historical os.getenv semantics)
        _write(config_file, BIND_AUTH_ENABLED="yes-please")
        assert cfg.get_bool("BIND_AUTH_ENABLED") is True

    def test_get_int_returns_value(self, tmp_path):
        config_file = tmp_path / "config.env"
        _write(config_file, SCRAPE_INTERVAL="120")
        cfg = LiveConfig(str(config_file), env={})
        assert cfg.get_int("SCRAPE_INTERVAL") == 120

    def test_get_int_garbage_falls_back_to_default(self, tmp_path):
        config_file = tmp_path / "config.env"
        _write(config_file, SCRAPE_INTERVAL="sixty")
        cfg = LiveConfig(str(config_file), env={})
        assert cfg.get_int("SCRAPE_INTERVAL") == int(ConfigManager.DEFAULTS["SCRAPE_INTERVAL"])

    def test_config_path_property(self, tmp_path):
        path = str(tmp_path / "config.env")
        assert LiveConfig(path, env={}).config_path == path
