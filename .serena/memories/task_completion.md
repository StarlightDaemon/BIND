# BIND — Task Completion Checklist

Run in order after any coding change:

```sh
ruff check src tests          # lint
ruff format src tests         # format
mypy src                      # type check (strict)
python -m pytest tests/ --cov=src --cov-report=term-missing -q   # tests + coverage (≥75%)
```

Coverage target is ≥85% (current: 94.51%, 547 tests passing).
