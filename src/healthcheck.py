"""Daemon liveness health check for container orchestration (DEP-2 / ARCH-1).

Exit 0 if the daemon heartbeat is fresh (within HEARTBEAT_MAX_AGE_S) or the
daemon is deliberately disabled; exit 1 otherwise (stale, no heartbeat row, or
no readable database). Intended as a Docker HEALTHCHECK for the daemon
container:

    python -m src.healthcheck
"""

import os
import sqlite3
import sys
from datetime import datetime, timezone

HEARTBEAT_MAX_AGE_S = 90


def check(db_path: str | None = None) -> int:
    db_path = db_path or os.getenv("BIND_DB_PATH", "data/bind.db")
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5.0)
    except sqlite3.OperationalError:
        return 1
    try:
        row = conn.execute("SELECT beat_at, state FROM daemon_heartbeat WHERE id = 1").fetchone()
    except sqlite3.OperationalError:
        return 1
    finally:
        conn.close()

    if row is None:
        return 1
    beat_at_s, state = row
    if state == "disabled":
        return 0
    try:
        beat_at = datetime.fromisoformat(beat_at_s)
    except (ValueError, TypeError):
        return 1
    if beat_at.tzinfo is None:
        beat_at = beat_at.replace(tzinfo=timezone.utc)
    age_s = (datetime.now(timezone.utc) - beat_at).total_seconds()
    return 0 if age_s <= HEARTBEAT_MAX_AGE_S else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(check())
