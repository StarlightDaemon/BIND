import sqlite3, pytest
from unittest.mock import MagicMock, patch
from src.core import storage


def test_probe_raises_if_wal_mode_not_accepted(tmp_path):
    db_path = str(tmp_path / "test.db")
    with patch("src.core.storage._open") as mock_open:
        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = ["delete"]  # not "wal"
        mock_open.return_value = conn
        with pytest.raises(RuntimeError, match="WAL mode not accepted"):
            storage._probe(db_path)
    conn.close.assert_called_once()


def test_probe_wraps_unexpected_exception(tmp_path):
    db_path = str(tmp_path / "test.db")
    with patch("src.core.storage._open") as mock_open:
        conn = MagicMock()
        # First call (journal_mode check) passes, second call raises
        conn.execute.side_effect = [
            MagicMock(**{"fetchone.return_value": ["wal"]}),
            Exception("fts5 not available"),
        ]
        mock_open.return_value = conn
        with pytest.raises(RuntimeError, match="Storage probe failed"):
            storage._probe(db_path)
    conn.close.assert_called_once()
