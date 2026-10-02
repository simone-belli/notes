---
tags:
  - typing
quiz: core
---

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

[`Literal`](../../language/typing/typing.md) restricts `side` to the two valid strings; Pydantic raises `ValidationError` at parse time for any other value.

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

## Parsing

`Trade(**data)` only works when the keys are valid Python identifiers and the data
is already a mapping. `model_validate` is the general entry point — one positional
argument, any supported input shape:

```python
from pydantic import ValidationError

Trade.model_validate({"symbol": "ES", "price": "5230.5", "qty": "10", "side": "BUY"})
Trade.model_validate_json('{"symbol":"ES","price":"5230.5","qty":10,"side":"BUY"}')
Trade.model_validate_strings({"symbol": "ES", "price": "5230.5", "qty": "10", "side": "BUY"})
```

- `model_validate(obj)` — dict (or, with `from_attributes`, any object).
- `model_validate_json(data)` — takes `str`/`bytes`; parses and validates in one
  Rust pass, so it is faster than `model_validate(json.loads(s))` and reports
  errors with the position in the original document.
- `model_validate_strings(obj)` — every leaf is a string; coerces per the field
  type. For query parameters, CSV rows, and environment variables.

Keyword arguments (all keyword-only):

```python
Trade.model_validate(row, strict=True)            # no coercion: "10" no longer satisfies int
Trade.model_validate(orm_row, from_attributes=True)   # read attributes, not keys
Trade.model_validate(data, context={"tz": "UTC"})     # reaches validators as info.context
```

- `strict=True` turns off type coercion for this call; `model_config = {"strict": True}`
  does it for the model, and `Field(strict=True)` for one field.
- `from_attributes=True` reads `obj.symbol` instead of `obj["symbol"]` — the
  Object-Relational Mapper (ORM) case. Set it on `model_config` to avoid repeating it.
- `context=` is passed through untouched to
  [validators](pydantic-validators.md) as `info.context`, which is how a validator
  gets a dependency it cannot import.
- `model_validate_json` accepts the same arguments **except** `from_attributes`.

### Failure

```python
try:
    Trade.model_validate({"symbol": "ES", "price": -1, "qty": "many", "side": "HOLD"})
except ValidationError as e:
    e.errors()      # list of dicts: loc, msg, type, input — one per failure
    e.json()        # same, as a JSON string
    len(e.errors()) # 3 — validation collects every error, it does not stop at the first
```

- `loc` is a tuple path into the input (`("price",)`, `("legs", 0, "qty")`), which
  is what makes nested errors actionable.
- `ValidationError` subclasses `ValueError`, so a bare `except ValueError` catches it.

!!! warning "`model_construct` skips validation entirely"
    `Trade.model_construct(**data)` builds the instance without validating or
    coercing anything — fast, and correct only for data a model already validated
    (a cache round-trip, a database row you wrote yourself). Pass it bad data and
    you get an object whose fields violate their own annotations. `model_copy(update=...)`
    has the same property: the update is **not** re-validated.

## TypeAdapter

Validation for types that aren't a `BaseModel` — a list of models, a bare `dict`,
a `Literal`, a `TypedDict`:

```python
from pydantic import TypeAdapter

adapter = TypeAdapter(list[Trade])
adapter.validate_python(rows)                   # → list[Trade]
adapter.validate_json(b'[{"symbol": "ES", ...}]')
adapter.dump_python(trades)
adapter.json_schema()
```

- Same method surface as a model, minus the `model_` prefix.
- Build the adapter **once** at module level and reuse it; construction compiles a
  validator and is the expensive part.
- Avoids the wrapper model whose only job is to hold a single `items: list[Trade]` field.

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

`model_dump_json()` accepts the same arguments and returns a JSON string directly — faster than `json.dumps(model.model_dump())` because Pydantic serialises without an intermediate dict. See [jsonl.md](../jsonl.md) for the file-persistence pattern.

## Notes
- BaseModel is the core Pydantic class
- Widely used with FastAPI
- Best used at application boundaries, not inside performance-critical loops
- Current major version is Pydantic v2


## When to use Pydantic vs dataclass (see [data-model.md](../../language/objects/classes/data-model.md#dataclass))?

!!! note "Pydantic at boundaries, dataclass for internal models"
    Pydantic validates and coerces untrusted data (API responses, user input, config files) at the edges of your system. Once data is inside, plain dataclasses are lighter and don't impose runtime validation overhead. Using Pydantic everywhere adds cost without benefit for objects that are constructed from already-validated data inside the system.

Rule: Pydantic at edges (input/output), dataclass for internal models

### Pydantic

For:
- validation
- serialisation = converting an object in memory into a format that can be: saved to disk; sent over a network; stored in a database; transmitted to another program. Usually this means converting Python objects into: JSON, bytes, text, dictionaries.
- for API boundaries

### dataclass

See [dataclasses.md](../../language/objects/dataclasses.md).

- stdlib
- lightweight
- no runtime validation
- for internal data