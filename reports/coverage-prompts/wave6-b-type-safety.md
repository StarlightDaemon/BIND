# Wave 6-B — Type Safety: Make mypy Strict Actually Strict

**Model: Claude Opus**
**Dependencies:** Waves 4 and 5 **committed** (this change touches signatures across the modules those waves rewrote — running it earlier creates churn and conflicts).
**Working directory:** `/Users/dante/Citadel/BIND`
**Activate the venv before any shell commands:** `source .venv/bin/activate`
**Finding remediated:** CQ-1 from `BIND_FULL_AUDIT_REPORT.md` (repo root — read it in full first).

## Why Opus for this task

The goal is not silencing mypy — it is making the type system catch the *class* of bug that already shipped (RES-2's exception misclassification lived inside a fully-`Any` function). Each `Any` removal is a small design decision about what the real contract is.

## Current state

`pyproject.toml` declares `strict = true`, then carves out:
- `disable_error_code = ["untyped-decorator", "no-any-return"]` for `src.rss_server`, `src.bind`, `src.security` — the three largest modules;
- `ignore_missing_imports` for `cloudscraper`, `bs4`, `schedule`, `flask`, `curl_cffi.*`, `click`, `werkzeug.*`;
- ~28 `Any` usages concentrated in the egress layer, the retry engine, and credential reads.

## Tasks (in order — each step must end with mypy green before the next)

1. **Drop `flask` and `werkzeug.*` from `ignore_missing_imports`.** Both ship inline types. Fix fallout properly: decorators get real signatures (`Callable[P, R]` with `ParamSpec` where wraps-preserving), `Response`/return types tightened. This alone likely clears most of the `untyped-decorator` need.
2. **Remove `disable_error_code` for the three modules.** Fix every resulting error with real types — `cast()` only where a value is genuinely narrowed by runtime logic mypy can't see, each with a one-line justification comment. Zero new `# type: ignore` is the target; if one is truly unavoidable, it must be error-code-scoped (`# type: ignore[code]`) and justified.
3. **HTTP response Protocol for the retry/egress seam.** Define in `src/core/retry.py` (or a new `src/core/http_types.py`):
   ```python
   class HTTPResponseLike(Protocol):
       status_code: int
       text: str
       @property
       def headers(self) -> Mapping[str, str]: ...
   ```
   Shape it to what the code actually touches (check `_parse_retry_after`'s `headers.get` usage and adjust — read the call sites, don't trust this sketch). Type `RetryEngine.execute` as `execute(fn: Callable[[], T], config: RetryConfig, layer_name: str) -> T | None` (generic, replacing `Any`), and type the duck-typed `getattr(e, "response", None)` access against `HTTPResponseLike | None`. The exception-classification logic from Wave 4-D must remain behavior-identical — its tests are the guard.
4. **Egress layer.** `EgressManager._cffi_session: Any` → type against the Protocol-relevant surface or the actual `curl_cffi.requests.Session` (curl_cffi 0.15 ships type hints — check `python -c "import curl_cffi.requests, inspect; ..."` / py.typed marker before deciding; if absent, keep `ignore_missing_imports` for `curl_cffi.*` and type the *boundary* — our wrapper methods' params/returns — instead). Remove the `cast(Any, response)` at the `raise_for_status` call if the chosen typing allows.
5. **Credentials dataclass.** Replace the `dict[str, Any]` credential blobs with a `@dataclass Credentials` (fields per the v3 schema from Wave 4-C — read `src/security.py` as it now stands) plus `from_dict`/`to_dict` doing explicit field validation with defaults. `load_credentials` returns `Credentials | None`; migrate call sites. This converts the silent-`KeyError`/`None`-propagation class of bug into validated loads. Keep the on-disk JSON format byte-compatible (key names, null handling) — the suite's migration tests are the guard.
6. **Leave alone:** `bs4`, `schedule`, `click`, `cloudscraper` ignores (no stubs worth chasing), and do NOT add new runtime dependencies (no pydantic — stdlib dataclasses only).

## Constraints

- Behavior-identical refactor: the full test suite must pass **unmodified** except where a test constructs the old credential dict shape directly — adapt those minimally and list them.
- `mypy src/` must pass with the tightened config; CI runs it, so `pyproject.toml` is the source of truth — no command-line flag tricks.
- Keep the diff reviewable: no opportunistic reformatting, no renames beyond what typing forces.

## Verification

```bash
source .venv/bin/activate
mypy src/                                   # green under the tightened config
grep -rn "type: ignore" src/ || echo "none" # each hit must be code-scoped + justified
grep -c "Any" src/core/retry.py             # expect ~0
python -m pytest tests/ -q
ruff check src/ tests/
```

## Done criteria

`disable_error_code` gone from pyproject; flask/werkzeug ignores gone; retry engine fully generic with zero `Any`; credentials flow through the dataclass; suite green; your summary lists every remaining `Any`/`cast`/`ignore` in `src/` with its justification.
