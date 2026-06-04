# BIND — Claude Project Instructions

## Agent prompt files

When building or refining prompts intended for another AI agent (Claude, Gemini, or any model):

- **Always write the prompt as a physical `.md` file.** Never present a full agent prompt inline in chat.
- Default location: `reports/coverage-prompts/`
- Naming convention: `wave<N>-<letter>-<short-descriptor>.md` (e.g. `wave1-a-rss-authenticated-routes.md`)
- After writing the file, link to it from the chat using relative markdown: `[filename](reports/coverage-prompts/filename.md)`
- The operator guide / README for a prompt set lives at `reports/coverage-prompts/README.md`

## Model naming

Use these exact strings — never older versions:

| Label | Correct name |
|---|---|
| 🔵 | Claude Sonnet |
| 🟣 | Gemini 3.1 Pro |
| 🟡 | Gemini 3 Flash |

## Gemini prompt format

Gemini prompts must be wrapped in a single fenced code block with the model as the language identifier. Nothing outside the block:

~~~
```gemini-3.1-pro
... entire prompt here ...
```
~~~

## Coverage work

- Coverage prompt files live in `reports/coverage-prompts/`
- Run coverage with: `python -m pytest tests/ --cov=src --cov-report=term-missing -q`
- Baseline: 76.54% — target: 85%+
- `--cov-fail-under=75` is set in `pyproject.toml`
- `BIND_AUTH_ENABLED=false` is set in `tests/conftest.py` — `@requires_auth` passes all requests in tests
- `CREDENTIALS_FILE = get_credentials_path()` in `src/security.py` is set at import time — always monkeypatch `src.security.CREDENTIALS_FILE` to `tmp_path` in any test touching credential functions
