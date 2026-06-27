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

The `Trade` model used here follows the pattern in [`pydantic.md`](../pydantic.md).

### Run

Pytest automatically:
- discovers files named test_*.py
- runs functions named test_*
- reports failures clearly

```bash
poetry run pytest
```
