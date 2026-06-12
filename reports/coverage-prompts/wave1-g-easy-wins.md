```gemini-3-flash
You are adding pytest tests to the BIND project to improve code coverage.
Working directory: /mnt/e/BIND
Activate the venv before running anything: source .venv/bin/activate

## Your task

Cover four small gaps across four modules. Create new test files where noted.
Do NOT modify existing test files.

---

## Target 1 — `src/__main__.py` (0% → 100%)

Missing: line 11 (the `cli()` call under `if __name__ == "__main__":`)

The file contains exactly:
```python
from src.bind import cli
if __name__ == "__main__":
    cli()
```

**Create** `tests/test_main.py`:
```python
import subprocess, sys

def test_main_module_is_importable():
    result = subprocess.run(
        [sys.executable, "-m", "src", "--help"],
        capture_output=True, text=True, cwd="/mnt/e/BIND"
    )
    assert result.returncode == 0
    assert "BIND" in result.stdout or "Usage" in result.stdout
```

Note: `pyproject.toml` excludes `if __name__ == "__main__":` via `exclude_lines`, so this
line is already excluded from coverage. Verify first:
```bash
python -m pytest tests/test_main.py -v --cov=src/__main__ --cov-report=term-missing
```
If `src/__main__.py` shows 100% after the import test, done. If not, the test above is sufficient.

---

## Target 2 — `src/core/migrate.py` (88% → 95%+)

Missing lines: 55, 63-64, 79-81, 92

- Line 55   → filename doesn't match the date regex → `continue`
- Lines 63–64 → `open(path)` raises `OSError` → warning + skip
- Lines 79–81 → DB `executemany` raises → `ROLLBACK` + re-raise
- Line 92   → `inserted != distinct` → raises `RuntimeError`

**Create** `tests/test_migrate.py`:

```python
import glob, os, sqlite3, pytest
from unittest.mock import MagicMock, patch

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
    (magnet_dir / "magnets_2024-01-01.txt").write_text("magnet:?xt=urn:btih:abc123def456789012345678901234567890abcd&dn=Test\n")
    db_path = str(tmp_path / "bind.db")
    with caplog.at_level(logging.WARNING, logger="migrate"):
        with patch("src.core.migrate.open", side_effect=OSError("permission denied")):
            migrate(str(magnet_dir), db_path)
    assert any("Skipping" in r.message for r in caplog.records)

def test_migrate_rollback_on_executemany_error(tmp_path):
    from src.core.migrate import migrate
    magnet_dir = tmp_path / "magnets"
    magnet_dir.mkdir()
    (magnet_dir / "magnets_2024-01-01.txt").write_text(
        "magnet:?xt=urn:btih:abc123def456789012345678901234567890abcd&dn=Test\n"
    )
    db_path = str(tmp_path / "bind.db")
    with patch("sqlite3.Connection.executemany", side_effect=Exception("db error")):
        with pytest.raises(Exception, match="db error"):
            migrate(str(magnet_dir), db_path)

def test_migrate_raises_on_row_count_mismatch(tmp_path):
    from src.core.migrate import migrate
    magnet_dir = tmp_path / "magnets"
    magnet_dir.mkdir()
    (magnet_dir / "magnets_2024-01-01.txt").write_text(
        "magnet:?xt=urn:btih:abc123def456789012345678901234567890abcd&dn=Test\n"
    )
    db_path = str(tmp_path / "bind.db")
    with patch("src.core.storage._open") as mock_open:
        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = [0]  # inserted = 0, parsed = 1
        conn.executemany = MagicMock()
        mock_open.return_value = conn
        with pytest.raises(RuntimeError, match="Row count mismatch"):
            migrate(str(magnet_dir), db_path)
```


---

## Target 3 — `src/core/tracker_manager.py` (84% → 95%+)

Missing lines: 39, 82-89, 102

- Line 39  → `load()` when `self.path` does not exist at call time → returns `DEFAULT_TRACKERS`
- Lines 82–89 → `save()` raises `OSError` → log error, cleanup tmp file, re-raise
- Line 102 → `get_default_trackers()` — never called in existing tests

**Append** to a new file `tests/test_tracker_manager_ext.py`:

```python
import os, pytest
from unittest.mock import patch
from src.core.tracker_manager import TrackerManager


def test_load_returns_defaults_when_file_missing(tmp_path):
    tm = TrackerManager(str(tmp_path))
    # Delete the file that __init__ just created
    tm.path.unlink()
    result = tm.load()
    assert result == TrackerManager.DEFAULT_TRACKERS


def test_get_default_trackers_returns_defaults(tmp_path):
    tm = TrackerManager(str(tmp_path))
    assert tm.get_default_trackers() == TrackerManager.DEFAULT_TRACKERS


def test_save_raises_and_cleans_up_tmp_on_oserror(tmp_path):
    tm = TrackerManager(str(tmp_path))
    with patch("os.replace", side_effect=OSError("no space")):
        with pytest.raises(OSError, match="no space"):
            tm.save(["udp://tracker.example.com:1337"])
    # tmp file should be cleaned up
    assert not tm.path.with_suffix(".json.tmp").exists()


def test_save_oserror_leaves_no_tmp_when_remove_also_fails(tmp_path):
    tm = TrackerManager(str(tmp_path))
    with patch("os.replace", side_effect=OSError("no space")):
        with patch("os.remove", side_effect=OSError("also broken")):
            with pytest.raises(OSError):
                tm.save(["udp://tracker.example.com:1337"])
```

---

## Target 4 — `src/core/storage.py` (93% → 98%+)

Missing lines: 65, 73-76

- Line 65  → `_probe()` WAL mode check fails → raises `RuntimeError`
- Lines 73–76 → `_probe()` non-RuntimeError exception → wrapped `RuntimeError`

**Append** to a new file `tests/test_storage_probe.py`:

```python
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
```

---

## Validation

Run each new file individually:
```bash
python -m pytest tests/test_main.py tests/test_migrate.py tests/test_tracker_manager_ext.py tests/test_storage_probe.py -v
```
All tests must pass. Then run the full suite to confirm no regressions:
```bash
python -m pytest tests/ -v --cov=src --cov-report=term-missing 2>&1 | tail -25
```
Report the final total coverage percentage.
```
