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

    @field_validator('symbol')  # see pydantic-validators.md for full validator docs
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

## Serialisation

```python
trade = Trade(symbol="AAPL", price=182.5, qty=10, side="BUY")

trade.model_dump()           # → dict  {"symbol": "AAPL", "price": Decimal("182.5"), ...}
trade.model_dump_json()      # → str   '{"symbol":"AAPL","price":"182.5",...}'
```

Key arguments to `model_dump()`:

```python
trade.model_dump(include={"symbol", "price"})    # only these fields
trade.model_dump(exclude={"qty"})                # all except these
trade.model_dump(exclude_none=True)              # drop fields whose value is None
trade.model_dump(exclude_unset=True)             # drop fields not explicitly set by the caller
trade.model_dump(mode="json")                    # coerce to JSON-safe types (e.g. Decimal → str)
```

`model_dump_json()` accepts the same arguments and returns a JSON string directly — faster than `json.dumps(model.model_dump())` because Pydantic serialises without an intermediate dict. See [jsonl.md](jsonl.md) for the file-persistence pattern.

## Notes
- BaseModel is the core Pydantic class
- Widely used with FastAPI
- Best used at application boundaries, not inside performance-critical loops
- Current major version is Pydantic v2


## When to use Pydantic vs dataclass (see [data-model.md](../language/objects/data-model.md#dataclass))?

!!! note "Pydantic at boundaries, dataclass for internal models"
    Pydantic validates and coerces untrusted data (API responses, user input, config files) at the edges of your system. Once data is inside, plain dataclasses are lighter and don't impose runtime validation overhead. Using Pydantic everywhere adds cost without benefit for objects that are constructed from already-validated data inside the system.

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