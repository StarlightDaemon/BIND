# BIND — Tech Stack

- **Python 3.10+**, packaged with `pyproject.toml` (PEP 517). No setup.py.
- **Package manager:** `uv` (`.venv/` at project root). `.venv.broken-wsl/` is a stale WSL2 artifact — ignore.
- **Web:** Flask 3.1.3, Gunicorn 26.0.0 (production server), CSRF via custom token middleware
- **HTTP egress:** `curl_cffi 0.15.0` (primary), `cloudscraper 1.2.71` (fallback), proxy pool rotation
- **HTML parsing:** `beautifulsoup4 4.12.3` + `lxml 6.1.0`
- **Scheduling:** `schedule 1.2.2` library (in-process), signal-file-based inter-process coordination
- **Storage:** SQLite (stdlib `sqlite3`) via `MagnetStore`; schema DDL in `storage._SCHEMA_DDL`
- **CLI:** `click 8.1.7`, entrypoint `bind = "src.bind:cli"`
- **Linter/formatter:** `ruff` (line-length 100, py310 target; `E501` ignored)
- **Type checker:** `mypy` strict mode; stubs missing for cloudscraper, bs4, schedule, flask, curl_cffi
- **Tests:** `pytest` + `pytest-cov` + `pytest-mock`; coverage threshold 75% (`--cov-fail-under=75`), current: 94.51% (target ≥85% exceeded)
- **Version:** 2.2.0
