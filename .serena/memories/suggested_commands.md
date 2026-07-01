# BIND — Suggested Commands

## Run / develop
```sh
# Run the daemon (foreground)
python -m src daemon

# Run the Flask dev server
python -m src serve   # or: flask --app src.rss_server run

# CLI help
bind --help
```

## Test & coverage
```sh
python -m pytest tests/ --cov=src --cov-report=term-missing -q
# Fail threshold is 75%; target is 85%+
BIND_AUTH_ENABLED=false python -m pytest   # auth disabled (set in conftest.py)
```

## Lint / format
```sh
ruff check src tests
ruff format src tests
```

## Type check
```sh
mypy src
```

## Notes (Darwin-specific)
- `.venv/` managed via `uv`; activate with `source .venv/bin/activate`
- `CREDENTIALS_FILE` in `src/security.py` is set at import time — monkeypatch `src.security.CREDENTIALS_FILE` in any test that touches credential functions
