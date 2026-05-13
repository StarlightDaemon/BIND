import logging
import sqlite3
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("storage")

_SCHEMA_DDL = [
    """CREATE TABLE IF NOT EXISTS magnets (
        id              INTEGER PRIMARY KEY,
        info_hash       TEXT    NOT NULL,
        title           TEXT    NOT NULL,
        collected_date  TEXT    NOT NULL,
        collected_at    TEXT    NOT NULL,
        source          TEXT    DEFAULT NULL
    )""",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_magnets_info_hash ON magnets(info_hash)",
    "CREATE INDEX IF NOT EXISTS idx_magnets_date_id ON magnets(collected_date DESC, id DESC)",
    """CREATE VIRTUAL TABLE IF NOT EXISTS magnets_fts USING fts5(
        title,
        content='magnets',
        content_rowid='id',
        tokenize='trigram'
    )""",
    """CREATE TRIGGER IF NOT EXISTS magnets_ai AFTER INSERT ON magnets BEGIN
        INSERT INTO magnets_fts(rowid, title) VALUES (new.id, new.title);
    END""",
    """CREATE TRIGGER IF NOT EXISTS magnets_ad AFTER DELETE ON magnets BEGIN
        INSERT INTO magnets_fts(magnets_fts, rowid, title) VALUES('delete', old.id, old.title);
    END""",
    """CREATE TRIGGER IF NOT EXISTS magnets_au AFTER UPDATE ON magnets BEGIN
        INSERT INTO magnets_fts(magnets_fts, rowid, title) VALUES('delete', old.id, old.title);
        INSERT INTO magnets_fts(rowid, title) VALUES(new.id, new.title);
    END""",
]


def _open(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30.0, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    for pragma in [
        "PRAGMA journal_mode = WAL",
        "PRAGMA synchronous = NORMAL",
        "PRAGMA busy_timeout = 5000",
        "PRAGMA temp_store = MEMORY",
        "PRAGMA cache_size = -20000",
        "PRAGMA foreign_keys = ON",
    ]:
        conn.execute(pragma)
    return conn


def _probe(db_path: str) -> None:
    conn = _open(db_path)
    try:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        if mode != "wal":
            raise RuntimeError(
                f"WAL mode not accepted (got '{mode}') — "
                "data directory may be on a network filesystem (e.g. WSL2 /mnt/)"
            )
        conn.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS _bind_fts_probe USING fts5(x, tokenize=trigram)"
        )
        conn.execute("DROP TABLE IF EXISTS _bind_fts_probe")
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"Storage probe failed: {e}") from e
    finally:
        conn.close()


class MagnetStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        _probe(db_path)
        self._conn = _open(db_path)
        self._init_schema()
        logger.info(f"MagnetStore ready at {db_path}")

    def _init_schema(self) -> None:
        for stmt in _SCHEMA_DDL:
            self._conn.execute(stmt)

    def close(self) -> None:
        self._conn.close()

    def add_magnet(
        self,
        info_hash: str,
        title: str,
        collected_date: str,
        source: Optional[str] = None,
    ) -> bool:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        cur = self._conn.execute(
            "INSERT OR IGNORE INTO magnets (info_hash, title, collected_date, collected_at, source)"
            " VALUES (?, ?, ?, ?, ?)",
            (info_hash.lower(), title, collected_date, now, source),
        )
        return cur.rowcount > 0

    def has_hash(self, info_hash: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM magnets WHERE info_hash = ? LIMIT 1",
            (info_hash.lower(),),
        ).fetchone()
        return row is not None

    def recent(self, limit: int = 100) -> list[dict]:
        rows = self._conn.execute(
            "SELECT info_hash, title, collected_date FROM magnets"
            " ORDER BY collected_date DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def search(
        self,
        query: Optional[str],
        page: int = 1,
        per_page: int = 50,
    ) -> tuple[list[dict], int]:
        offset = (page - 1) * per_page

        if not query:
            rows = self._conn.execute(
                "SELECT info_hash, title, collected_date FROM magnets"
                " ORDER BY collected_date DESC, id DESC LIMIT ? OFFSET ?",
                (per_page, offset),
            ).fetchall()
            total = self._conn.execute("SELECT COUNT(*) FROM magnets").fetchone()[0]
            return [dict(r) for r in rows], total

        pattern = f"%{query}%"

        if len(query) < 3:
            # Short query: FTS trigram needs ≥3 chars; fall back to full scan
            rows = self._conn.execute(
                "SELECT info_hash, title, collected_date FROM magnets"
                " WHERE title LIKE ? COLLATE NOCASE"
                " ORDER BY collected_date DESC, id DESC LIMIT ? OFFSET ?",
                (pattern, per_page, offset),
            ).fetchall()
            total = self._conn.execute(
                "SELECT COUNT(*) FROM magnets WHERE title LIKE ? COLLATE NOCASE",
                (pattern,),
            ).fetchone()[0]
        else:
            rows = self._conn.execute(
                "SELECT m.info_hash, m.title, m.collected_date"
                " FROM magnets m JOIN magnets_fts f ON f.rowid = m.id"
                " WHERE f.title LIKE ?"
                " ORDER BY m.collected_date DESC, m.id DESC LIMIT ? OFFSET ?",
                (pattern, per_page, offset),
            ).fetchall()
            total = self._conn.execute(
                "SELECT COUNT(*) FROM magnets_fts WHERE title LIKE ?",
                (pattern,),
            ).fetchone()[0]

        return [dict(r) for r in rows], total

    def stats(self) -> dict:
        today = datetime.now().strftime("%Y-%m-%d")
        total = self._conn.execute("SELECT COUNT(*) FROM magnets").fetchone()[0]
        today_count = self._conn.execute(
            "SELECT COUNT(*) FROM magnets WHERE collected_date = ?",
            (today,),
        ).fetchone()[0]
        last_row = self._conn.execute(
            "SELECT collected_date FROM magnets ORDER BY collected_date DESC, id DESC LIMIT 1"
        ).fetchone()
        return {
            "total": total,
            "today": today_count,
            "last_date": last_row[0] if last_row else None,
        }
