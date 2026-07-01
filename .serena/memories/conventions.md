# BIND — Conventions

## Code style
- Line length: 100 (ruff), `E501` ignored.
- Python 3.10+ (unions with `|`, match, etc. allowed).
- Double quotes (ruff format default).
- Module-level `logger = logging.getLogger(__name__)` in every module.
- Type hints throughout; mypy strict. Stubs missing for several third-party libs (see `mem:tech_stack`).

## Patterns
- **Config access:** `LiveConfig` for read-only runtime access (no restart); `ConfigManager` for write + restart.
- **Auth decorator:** `@requires_auth` in `security.py` — wraps Flask routes. In tests, `BIND_AUTH_ENABLED=false` bypasses it.
- **Credential tests:** always monkeypatch `src.security.CREDENTIALS_FILE` → `tmp_path` (set at import time).
- **Egress:** always go through `EgressManager`; never direct `requests` calls. Proxy pool handles rotation + cooldown.
- **Retry logic:** use `RetryEngine` from `core/retry.py`; configure via `RetryConfig`.
- **CircuitBreaker** in `scraper.py` gates individual scrape attempts per target.
- **SchemaHealthMonitor** detects parse-success drift across scraping runs — triggers alerting.
- **Storage mutations** are funnelled through `MagnetStore` methods; no raw SQL outside `storage.py`.
- **Migration:** `core/migrate.py` is a one-shot import of legacy flat files; not re-run once done.

## Testing
- `tests/conftest.py` sets `BIND_AUTH_ENABLED=false` globally.
- Coverage prompt files live in `reports/coverage-prompts/`; run coverage with `python -m pytest tests/ --cov=src --cov-report=term-missing -q`.
- Coverage: 94.51% (547 tests passing). Target ≥85% (exceeded).
