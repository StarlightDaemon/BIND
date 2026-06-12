"""Extended resilience tests targeting coverage gaps in:
- src/core/retry.py   (lines 88, 98, 101-104)
- src/core/migrate.py (0% → covered)
- src/security.py     (log_security_event file write, _migrate_credentials)
"""

import json
import os
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# src/core/retry.py — missing branches
# ---------------------------------------------------------------------------


class TestRetryEngineMissingBranches:
    """Cover the remaining uncovered lines in RetryEngine."""

    def _engine(self):
        from src.core.retry import RetryConfig, RetryEngine

        return RetryEngine(), RetryConfig

    def test_loop_falls_through_all_retries_returns_none(self):
        """Line 88: the final `return None` after all attempts via ConnectionError."""
        from src.core.retry import RetryConfig, RetryEngine

        engine = RetryEngine()
        config = RetryConfig(max_attempts=3, base_delay=0)
        fn = MagicMock(side_effect=ConnectionError("net"))
        with patch("time.sleep"):
            result = engine.execute(fn, config, "layer")
        # All 3 attempts exhausted via the transient branch → falls to line 88
        assert result is None
        assert fn.call_count == 3

    def test_parse_retry_after_returns_none_when_response_is_none(self):
        """Line 98: _parse_retry_after(None) returns None immediately."""
        from src.core.retry import RetryEngine

        assert RetryEngine._parse_retry_after(None) is None

    def test_parse_retry_after_returns_float_for_valid_header(self):
        """Lines 101-102: valid Retry-After header is parsed to float."""
        from src.core.retry import RetryEngine

        response = MagicMock()
        response.headers.get = MagicMock(return_value="30")
        result = RetryEngine._parse_retry_after(response)
        assert result == 30.0

    def test_parse_retry_after_returns_none_for_invalid_header(self):
        """Lines 103-104: non-numeric Retry-After header returns None."""
        from src.core.retry import RetryEngine

        response = MagicMock()
        response.headers.get = MagicMock(return_value="not-a-number")
        result = RetryEngine._parse_retry_after(response)
        assert result is None

    def test_parse_retry_after_returns_none_when_no_header(self):
        """Line 98+: header absent → returns None."""
        from src.core.retry import RetryEngine

        response = MagicMock()
        response.headers.get = MagicMock(return_value=None)
        result = RetryEngine._parse_retry_after(response)
        assert result is None

    def test_429_uses_retry_after_header_when_present(self):
        """429 with a Retry-After header uses the parsed wait time."""
        from src.core.retry import RetryConfig, RetryEngine

        engine = RetryEngine()
        config = RetryConfig(max_attempts=2, base_delay=1.0)

        exc = Exception("rate limited")
        resp = MagicMock()
        resp.status_code = 429
        resp.headers.get = MagicMock(return_value="5")
        exc.response = resp  # type: ignore[attr-defined]

        fn = MagicMock(side_effect=[exc, "ok"])
        with patch("time.sleep") as mock_sleep:
            result = engine.execute(fn, config, "layer")
        assert result == "ok"
        mock_sleep.assert_called_once_with(5.0)


# ---------------------------------------------------------------------------
# src/core/migrate.py — entire module (0% → covered)
# ---------------------------------------------------------------------------


class TestMigrate:
    """Tests for _parse_line and migrate() in src/core/migrate.py."""

    def test_parse_line_valid_magnet(self):
        """_parse_line returns a tuple for a well-formed magnet URI."""
        from src.core.migrate import _parse_line

        line = (
            "magnet:?xt=urn:btih:aabbccdd11223344556677889900112233445566"
            "&dn=My+Great+Audiobook&tr=udp://tracker.example.com:80"
        )
        result = _parse_line(line, "2024-01-15")
        assert result is not None
        info_hash, title, date, collected_at, source = result
        assert info_hash == "aabbccdd11223344556677889900112233445566"
        assert title == "My Great Audiobook"
        assert date == "2024-01-15"
        assert source is None

    def test_parse_line_skips_non_magnet(self):
        """_parse_line returns None for lines that don't start with 'magnet:'."""
        from src.core.migrate import _parse_line

        assert _parse_line("# comment line", "2024-01-01") is None
        assert _parse_line("", "2024-01-01") is None
        assert _parse_line("http://example.com/book", "2024-01-01") is None

    def test_parse_line_skips_missing_hash(self):
        """_parse_line returns None when no xt=urn:btih hash is present."""
        from src.core.migrate import _parse_line

        line = "magnet:?dn=Book+Title&tr=udp://tracker.example.com:80"
        assert _parse_line(line, "2024-01-01") is None

    def test_parse_line_skips_missing_dn(self):
        """_parse_line returns None when no dn= display name is present."""
        from src.core.migrate import _parse_line

        line = "magnet:?xt=urn:btih:aabbccdd1122334455667788990011223344556677"
        assert _parse_line(line, "2024-01-01") is None

    def test_migrate_no_files(self, tmp_path):
        """migrate() with an empty magnets_dir logs and returns without error."""
        from src.core.migrate import migrate

        magnets_dir = tmp_path / "magnets"
        magnets_dir.mkdir()
        db_path = str(tmp_path / "bind.db")
        # Should not raise even with no .txt files
        migrate(str(magnets_dir), db_path)

    def test_migrate_inserts_rows(self, tmp_path):
        """migrate() inserts parsed magnet lines into the SQLite database."""
        import sqlite3

        from src.core.migrate import migrate

        magnets_dir = tmp_path / "magnets"
        magnets_dir.mkdir()
        db_path = str(tmp_path / "bind.db")

        magnet_line = (
            "magnet:?xt=urn:btih:aabbccdd11223344556677889900112233445566"
            "&dn=Great+Audiobook&tr=udp://tracker.example.com:80\n"
        )
        magnet_file = magnets_dir / "magnets_2024-01-15.txt"
        magnet_file.write_text(magnet_line, encoding="utf-8")

        migrate(str(magnets_dir), db_path)

        conn = sqlite3.connect(db_path)
        count = conn.execute("SELECT COUNT(*) FROM magnets").fetchone()[0]
        title = conn.execute("SELECT title FROM magnets LIMIT 1").fetchone()[0]
        conn.close()
        assert count == 1
        assert title == "Great Audiobook"

    def test_migrate_deduplicates_by_hash(self, tmp_path):
        """migrate() uses INSERT OR IGNORE, so duplicate hashes result in one row."""
        import sqlite3

        from src.core.migrate import migrate

        magnets_dir = tmp_path / "magnets"
        magnets_dir.mkdir()
        db_path = str(tmp_path / "bind.db")

        # Two files with the same hash
        line = (
            "magnet:?xt=urn:btih:aabbccdd11223344556677889900112233445566"
            "&dn=Same+Book&tr=udp://tracker.example.com:80\n"
        )
        (magnets_dir / "magnets_2024-01-01.txt").write_text(line, encoding="utf-8")
        (magnets_dir / "magnets_2024-01-02.txt").write_text(line, encoding="utf-8")

        migrate(str(magnets_dir), db_path)

        conn = sqlite3.connect(db_path)
        count = conn.execute("SELECT COUNT(*) FROM magnets").fetchone()[0]
        conn.close()
        assert count == 1

    def test_migrate_skips_files_without_date_pattern(self, tmp_path):
        """Files that don't match magnets_YYYY-MM-DD.txt are silently skipped."""
        import sqlite3

        from src.core.migrate import migrate

        magnets_dir = tmp_path / "magnets"
        magnets_dir.mkdir()
        db_path = str(tmp_path / "bind.db")

        # File with wrong name pattern
        (magnets_dir / "some_other_file.txt").write_text(
            "magnet:?xt=urn:btih:aabbccdd11223344556677889900112233445566&dn=Hidden+Book\n",
            encoding="utf-8",
        )

        migrate(str(magnets_dir), db_path)

        conn = sqlite3.connect(db_path)
        count = conn.execute("SELECT COUNT(*) FROM magnets").fetchone()[0]
        conn.close()
        # No rows inserted because file wasn't matched
        assert count == 0

    def test_migrate_multiple_files(self, tmp_path):
        """migrate() correctly processes multiple date-stamped files."""
        import sqlite3

        from src.core.migrate import migrate

        magnets_dir = tmp_path / "magnets"
        magnets_dir.mkdir()
        db_path = str(tmp_path / "bind.db")

        for i, date in enumerate(["2024-01-01", "2024-01-02", "2024-01-03"]):
            hash_val = f"{'0' * 38}{i:02d}"
            line = f"magnet:?xt=urn:btih:{hash_val}&dn=Book+{i}&tr=udp://tracker.example.com:80\n"
            (magnets_dir / f"magnets_{date}.txt").write_text(line, encoding="utf-8")

        migrate(str(magnets_dir), db_path)

        conn = sqlite3.connect(db_path)
        count = conn.execute("SELECT COUNT(*) FROM magnets").fetchone()[0]
        conn.close()
        assert count == 3


# ---------------------------------------------------------------------------
# src/security.py — log_security_event file write + _migrate_credentials
# ---------------------------------------------------------------------------


class TestSecurityLogEvent:
    """Cover log_security_event's file-write path (lines 73-93)."""

    def test_log_security_event_writes_to_file(self, tmp_path, monkeypatch):
        """log_security_event writes a line to the security log file."""
        log_path = str(tmp_path / "security.log")
        monkeypatch.setattr("src.security.get_security_log_path", lambda: log_path)
        monkeypatch.setattr("src.security._rotate_log_if_needed", lambda p, max_lines=1000: None)

        from src.security import log_security_event

        log_security_event("LOGIN_SUCCESS", "admin", "127.0.0.1", "test")

        assert os.path.exists(log_path)
        content = open(log_path, encoding="utf-8").read()
        assert "LOGIN_SUCCESS" in content
        assert "admin" in content

    def test_log_security_event_oserror_is_silent(self, tmp_path, monkeypatch):
        """log_security_event silently ignores OSError on log write (line 92-93)."""
        monkeypatch.setattr(
            "src.security.get_security_log_path",
            lambda: "/nonexistent/dir/security.log",
        )

        from src.security import log_security_event

        # Must not raise
        log_security_event("LOGIN_FAILED", "admin", "1.2.3.4")

    def test_rotate_log_if_needed_trims_when_over_limit(self, tmp_path):
        """_rotate_log_if_needed trims file to max_lines when exceeded."""
        from src.security import _rotate_log_if_needed

        log_path = str(tmp_path / "security.log")
        lines = [f"line {i}\n" for i in range(20)]
        with open(log_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

        _rotate_log_if_needed(log_path, max_lines=5)

        with open(log_path, encoding="utf-8") as f:
            remaining = f.readlines()
        assert len(remaining) == 5
        assert remaining[0] == "line 15\n"

    def test_rotate_log_if_needed_no_op_under_limit(self, tmp_path):
        """_rotate_log_if_needed does nothing when file is within max_lines."""
        from src.security import _rotate_log_if_needed

        log_path = str(tmp_path / "security.log")
        lines = [f"line {i}\n" for i in range(3)]
        with open(log_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

        _rotate_log_if_needed(log_path, max_lines=10)

        with open(log_path, encoding="utf-8") as f:
            remaining = f.readlines()
        assert len(remaining) == 3


class TestMigrateCredentials:
    """Cover _migrate_credentials (lines 141-157)."""

    def test_migrate_adds_v2_fields(self, tmp_path, monkeypatch):
        """_migrate_credentials upgrades v1 creds dict to v2 schema."""
        cred_path = str(tmp_path / "credentials.json")
        monkeypatch.setattr("src.security.CREDENTIALS_FILE", cred_path)

        v1_creds = {
            "version": 1,
            "username": "admin",
            "password_hash": "pbkdf2:sha256:xxx",
            "created_at": "2024-01-01T00:00:00Z",
        }
        # Write v1 credentials
        with open(cred_path, "w", encoding="utf-8") as f:
            json.dump(v1_creds, f)

        from src.security import _migrate_credentials

        result = _migrate_credentials(v1_creds.copy())
        assert result["version"] == 3
        assert "failed_attempts" in result
        assert "locked_until" in result
        assert "last_login" in result
        assert result["failed_by_ip"] == {}

    def test_load_credentials_triggers_migration(self, tmp_path, monkeypatch):
        """load_credentials auto-migrates v1 creds when file contains version=1."""
        cred_path = str(tmp_path / "credentials.json")
        monkeypatch.setattr("src.security.CREDENTIALS_FILE", cred_path)

        v1_creds = {
            "version": 1,
            "username": "admin",
            "password_hash": "pbkdf2:sha256:xxx",
            "created_at": "2024-01-01T00:00:00Z",
        }
        with open(cred_path, "w", encoding="utf-8") as f:
            json.dump(v1_creds, f)

        import src.security as sec

        monkeypatch.setattr(sec, "CREDENTIALS_FILE", cred_path)

        result = sec.load_credentials()
        assert result["version"] == 3
        assert result.get("failed_attempts") == 0


class TestGetBaseDir:
    """Cover get_base_dir alternative path (line 45)."""

    def test_returns_opt_bind_when_exists(self, monkeypatch):
        """get_base_dir returns '/opt/bind' when that path exists."""
        monkeypatch.setattr("os.path.exists", lambda p: p == "/opt/bind")

        import src.security as sec

        result = sec.get_base_dir()
        assert result == "/opt/bind"

    def test_returns_project_root_when_opt_bind_missing(self):
        """get_base_dir returns the project root when /opt/bind doesn't exist."""
        from src.security import get_base_dir

        result = get_base_dir()
        # Should be a real directory, not /opt/bind (since we're in dev)
        assert os.path.isdir(result)
        assert result != "/opt/bind"
