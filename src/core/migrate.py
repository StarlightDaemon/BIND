"""
One-shot migration from flat magnets_YYYY-MM-DD.txt files to SQLite.

Usage:
    python -m src.core.migrate --magnets-dir data/magnets --db-path data/bind.db
"""

import argparse
import glob
import logging
import os
import re
from urllib.parse import unquote_plus

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("migrate")

_RE_BTIH = re.compile(r"xt=urn:btih:([0-9a-fA-F]{40})", re.IGNORECASE)
_RE_DN = re.compile(r"[?&]dn=([^&]+)")
_RE_DATE = re.compile(r"magnets_(\d{4}-\d{2}-\d{2})\.txt$")


def _parse_line(line: str, date_str: str) -> tuple | None:
    line = line.strip()
    if not line.startswith("magnet:"):
        return None
    m_hash = _RE_BTIH.search(line)
    m_dn = _RE_DN.search(line)
    if not m_hash or not m_dn:
        return None
    info_hash = m_hash.group(1).lower()
    title = unquote_plus(m_dn.group(1))
    collected_at = f"{date_str}T00:00:00.000Z"
    return (info_hash, title, date_str, collected_at, None)


def migrate(magnets_dir: str, db_path: str) -> None:
    from src.core.storage import _SCHEMA_DDL, _open

    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)

    conn = _open(db_path)
    for stmt in _SCHEMA_DDL:
        conn.execute(stmt)

    files = sorted(glob.glob(os.path.join(magnets_dir, "magnets_*.txt")))
    if not files:
        logger.info("No magnet files found — nothing to migrate.")
        return

    rows: list[tuple] = []
    for path in files:
        m = _RE_DATE.search(os.path.basename(path))
        if not m:
            continue
        date_str = m.group(1)
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                for line in f:
                    row = _parse_line(line, date_str)
                    if row:
                        rows.append(row)
        except OSError as e:
            logger.warning(f"Skipping {path}: {e}")

    parsed = len(rows)
    distinct = len({r[0] for r in rows})
    logger.info(f"Parsed {parsed} lines, {distinct} distinct hashes from {len(files)} files")

    conn.execute("BEGIN")
    try:
        conn.executemany(
            "INSERT OR IGNORE INTO magnets"
            " (info_hash, title, collected_date, collected_at, source)"
            " VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    # Safety rebuild in case triggers misfired during bulk insert
    conn.execute("INSERT INTO magnets_fts(magnets_fts) VALUES ('rebuild')")
    conn.execute("ANALYZE")

    inserted = conn.execute("SELECT COUNT(*) FROM magnets").fetchone()[0]
    conn.close()

    logger.info(f"Inserted {inserted} rows (expected {distinct})")
    if inserted != distinct:
        raise RuntimeError(f"Row count mismatch: inserted={inserted} distinct_hashes={distinct}")
    logger.info("Migration complete. Flat files are untouched — archive or delete manually.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate BIND flat files to SQLite")
    parser.add_argument("--magnets-dir", default="data/magnets")
    parser.add_argument("--db-path", default="data/bind.db")
    args = parser.parse_args()
    migrate(args.magnets_dir, args.db_path)
