---
tags:
  - testing
---

# pytest

pytest is the standard Python testing framework. It automatically discovers files named `test_*.py` and functions named `test_*`.

## Installation

```bash
poetry add --group dev pytest
```

## Usage

### Generate a test file

```python
def test_rejects_negative_quantity():
    with pytest.raises(Exception):
        Trade(symbol='BHP', quantity=-10, price=45.5, side='BUY')
```

The `Trade` model used here follows the pattern in [`pydantic.md`](../../libraries/pydantic/pydantic.md).

### `pytest.raises(..., match=)`

`match=` checks the exception message against a [regex](../../../tools/regexp.md), so the test verifies both the error type *and* that the message is actually useful:

```python
def test_rejects_negative_quantity():
    with pytest.raises(ValueError, match="quantity must be positive"):
        Trade(symbol='BHP', quantity=-10, price=45.5, side='BUY')
```

Without `match=`, a test can pass even if the exception message is empty or unhelpful.

### Run

Pytest automatically:
- discovers files named test_*.py
- runs functions named test_*
- reports failures clearly

```bash
poetry run pytest
```

### Selecting specific tests

Every test has a **node ID** of the form `path::function` (`::Class::method` for
methods on a class). Pass it to run exactly one test:

```bash
pytest tests/test_trade.py                          # every test in the file
pytest tests/test_trade.py::test_rejects_negative   # one function
pytest tests/test_trade.py::TestTrade::test_buy     # one method on a class
```

Each `@pytest.mark.parametrize` case gets a **parameter ID** in square brackets;
append it to run a single case (quote it — `[]` are shell glob characters):

```bash
pytest --collect-only tests/test_trade.py   # list the exact IDs first
# tests/test_trade.py::test_side[BUY]

pytest "tests/test_trade.py::test_side[BUY]"   # just that one parametrized case
```

!!! tip "Node IDs vs `-k`"
    Node IDs are exact. `-k EXPR` selects by *name substring* with `and`/`or`/`not`
    (`pytest -k "side and BUY"`), and `-m EXPR` selects by marker (`pytest -m slow`).
    Use `-k` when you remember only part of a name; use the node ID when you want one
    precise test.

Discovery and re-run helpers:

```bash
pytest --collect-only   # show all node IDs without running (--co -q for short)
pytest --lf             # re-run only last-failed
pytest -x               # stop at first failure
```

## Coverage

Install `pytest-cov`, then use `--cov-report=term-missing` to see which line numbers are uncovered:

```bash
pytest --cov=mypackage --cov-report=term-missing
```

```
Name                Stmts   Miss  Cover   Missing
-------------------------------------------------
mypackage/store.py     42      7    83%   34-36, 58, 72-74
mypackage/trade.py     18      0   100%
```

```bash
# Skip already-covered files
pytest --cov=mypackage --cov-report=term-missing:skip-covered

# HTML report (open htmlcov/index.html — uncovered lines highlighted)
pytest --cov=mypackage --cov-report=html

# Fail if coverage drops below threshold
pytest --cov=mypackage --cov-fail-under=80
```

Persist flags in `pyproject.toml` so you don't retype them:

```toml
[tool.pytest.ini_options]
addopts = "--cov=mypackage --cov-report=term-missing:skip-covered"
```
