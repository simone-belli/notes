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

## Approximate equality

Floating-point results carry representation error, so `==` fails on values that are mathematically equal ([why](../../language/objects/numbers.md#float-comparison)). Wrap the **expected** value in `pytest.approx`:

```python
import pytest

def test_total():
    assert 0.1 + 0.2 == pytest.approx(0.3)
```

Two values match when `abs(actual - expected) <= max(rel * abs(expected), abs)` — the relative and absolute bounds are OR'd, so either one passing is enough. Defaults are `rel=1e-6`, `abs=1e-12`.

```python
pytest.approx(0.3, rel=1e-3)   # within 0.1% of the expected value
pytest.approx(0.0, abs=1e-9)   # near zero — rel collapses, abs carries it
```

### What `approx` accepts

| Expected | Behaviour |
|---|---|
| scalar | `0.1 + 0.2 == approx(0.3)` |
| list / tuple | element-wise; lengths must match |
| dict | value-wise; differing keys compare unequal rather than raising |
| numpy array | element-wise |
| set | `TypeError` — `approx` needs an ordered sequence |

!!! warning "`nan` never equals itself, even under `approx`"
    `float("nan") == pytest.approx(float("nan"))` is `False`. `nan_ok=True` flips that, but it accepts a `nan` *anywhere* in a sequence — usually you want an explicit `math.isnan(x)` assertion instead, so a stray `nan` still fails the test.

### Arrays and DataFrames

`approx` handles both, but the dedicated helpers report *which* elements differ:

```python
import numpy.testing as npt
from pandas.testing import assert_frame_equal

npt.assert_allclose(actual, desired, rtol=1e-7, atol=0)   # defaults shown
assert_frame_equal(left, right, rtol=1e-5, atol=1e-8)     # defaults shown
```

- `assert_allclose` defaults to `atol=0`, so it fails on expected values of exactly zero — pass `atol` explicitly there.
- `assert_frame_equal` compares float columns with tolerance by default, and also checks dtype, column order, and index; `check_exact=True` forces exact comparison.

!!! tip "Pick the tolerance from the computation, not from the failure"
    A tolerance widened until the test goes green no longer detects a regression. Derive it from accumulated rounding over the operations involved, or from the precision the code under test documents.

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
