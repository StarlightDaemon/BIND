import sqlite3
from unittest.mock import MagicMock, patch

import pytest


def test_migrate_skips_files_without_date_in_name(tmp_path):
    from src.core.migrate import migrate

    magnet_dir = tmp_path / "magnets"
    magnet_dir.mkdir()
    # File with name that doesn't match magnets_YYYY-MM-DD.txt
    (magnet_dir / "notadate.txt").write_text(
        "magnet:?xt=urn:btih:abc123def456789012345678901234567890abcd&dn=Test\n"
    )
    db_path = str(tmp_path / "bind.db")
    migrate(str(magnet_dir), db_path)
    conn = sqlite3.connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM magnets").fetchone()[0]
    conn.close()
    assert count == 0  # skipped the bad filename


def test_migrate_warns_on_oserror_opening_file(tmp_path, caplog):
    import logging

    from src.core.migrate import migrate

    magnet_dir = tmp_path / "magnets"
    magnet_dir.mkdir()
    (magnet_dir / "magnets_2024-01-01.txt").write_text(
        "magnet:?xt=urn:btih:abc123def456789012345678901234567890abcd&dn=Test\n"
    )
    db_path = str(tmp_path / "bind.db")
    with caplog.at_level(logging.WARNING, logger="migrate"):
        with patch("builtins.open", side_effect=OSError("permission denied")):
            migrate(str(magnet_dir), db_path)
    assert any("Skipping" in r.message for r in caplog.records)


def test_migrate_rollback_on_executemany_error(tmp_path):
    from src.core import storage
    from src.core.migrate import migrate

    magnet_dir = tmp_path / "magnets"
    magnet_dir.mkdir()
    (magnet_dir / "magnets_2024-01-01.txt").write_text(
        "magnet:?xt=urn:btih:abc123def456789012345678901234567890abcd&dn=Test\n"
    )
    db_path = str(tmp_path / "bind.db")

    class ConnectionProxy:
        def __init__(self, real_conn):
            self._conn = real_conn

        def __getattr__(self, name):
            return getattr(self._conn, name)

        def executemany(self, sql, seq_of_parameters):
            raise Exception("db error")

    original_open = storage._open

    def mock_open(path):
        conn = original_open(path)
        return ConnectionProxy(conn)

    with patch("src.core.storage._open", side_effect=mock_open):
        with pytest.raises(Exception, match="db error"):
            migrate(str(magnet_dir), db_path)


def test_migrate_raises_on_row_count_mismatch(tmp_path):
    from src.core import storage
    from src.core.migrate import migrate

    magnet_dir = tmp_path / "magnets"
    magnet_dir.mkdir()
    line = "magnet:?xt=urn:btih:abc123def456789012345678901234567890abcd&dn=Test\n"
    (magnet_dir / "magnets_2024-01-01.txt").write_text(line)
    db_path = str(tmp_path / "bind.db")

    class ConnectionProxy:
        def __init__(self, real_conn):
            self._conn = real_conn

        def __getattr__(self, name):
            return getattr(self._conn, name)

        def execute(self, sql, *args, **kwargs):
            if "SELECT COUNT(*)" in sql:
                mock_cursor = MagicMock()
                mock_cursor.fetchone.return_value = [0]
                return mock_cursor
            return self._conn.execute(sql, *args, **kwargs)

    original_open = storage._open

    def mock_open(path):
        conn = original_open(path)
        return ConnectionProxy(conn)

    with patch("src.core.storage._open", side_effect=mock_open):
        with pytest.raises(RuntimeError, match="Row count mismatch"):
            migrate(str(magnet_dir), db_path)


def test_migrate_happy_path(tmp_path):
    from src.core.migrate import migrate

    magnet_dir = tmp_path / "magnets"
    magnet_dir.mkdir()
    line = "magnet:?xt=urn:btih:abc123def456789012345678901234567890abcd&dn=Test\n"
    (magnet_dir / "magnets_2024-01-01.txt").write_text(line)
    db_path = str(tmp_path / "bind.db")
    migrate(str(magnet_dir), db_path)
    conn = sqlite3.connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM magnets").fetchone()[0]
    conn.close()
    assert count == 1
