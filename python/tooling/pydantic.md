# Pydantic

Pydantic is a Python library used for data validation and parsing using type hints.

## Main Idea

You define the structure of your data as Python classes, and Pydantic:
- validates incoming data
- converts compatible types automatically
- raises clear errors for invalid data

## Basic Example

```python
from pydantic import BaseModel, Field, field_validator
from decimal import Decimal
from typing import Literal

class Trade(BaseModel):
    model_config = {'frozen': True, 'str_strip_whitespace': True}

    symbol: str = Field(..., min_length=1, max_length=10)
    price: Decimal = Field(..., gt=0)
    qty: int
    side: Literal['BUY', 'SELL']

    @field_validator('symbol')  # for custom validation logic
    @classmethod
    def symbol_uppercase(cls, v: str) -> str:
        return v.upper()

    @property
    def notional(self) -> Decimal:
        return self.quantity * self.price

trade = Trade(symbol="ES", price="5230.5", qty="10", side="BUY")
```

[`Literal`](../language/objects/typing.md) restricts `side` to the two valid strings; Pydantic raises `ValidationError` at parse time for any other value.

## Typical Uses

- API request/response validation
- Parsing JSON data
- Data pipelines and ETL
- LLM structured outputs
- Configuration management and env vars → see [pydantic-settings.md](pydantic-settings.md)

## Common Features
- Runtime type checking
- Automatic type coercion
- Clear validation errors
- Nested models
- Optional/default fields
- JSON serialization

## Notes
- BaseModel is the core Pydantic class
- Widely used with FastAPI
- Best used at application boundaries, not inside performance-critical loops
- Current major version is Pydantic v2


## When to use Pydantic vs dataclass (see [data-model.md](../language/objects/data-model.md#dataclass))?

Rule: Pydantic at edges (input/output), dataclass for internal models

### Pydantic

For:
- validation
- serialisation = converting an object in memory into a format that can be: saved to disk; sent over a network; stored in a database; transmitted to another program. Usually this means converting Python objects into: JSON, bytes, text, dictionaries.
- for API boundaries

### dataclass

- stdlib
- lightweight
- no runtime validation
- for internal data