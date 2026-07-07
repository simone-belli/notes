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

The `Trade` model used here follows the pattern in [`pydantic.md`](../pydantic/pydantic.md).

### Run

Pytest automatically:
- discovers files named test_*.py
- runs functions named test_*
- reports failures clearly

```bash
poetry run pytest
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
