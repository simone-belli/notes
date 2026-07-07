# Pydantic — Validators

Two families: `@field_validator` (one field) and `@model_validator` (whole model). Each runs in `before` (raw input) or `after` (parsed) mode.

Use `Field(gt=0, min_length=1, ...)` for simple constraints first — write a validator only when the logic exceeds what `Field()` can express.

---

## @field_validator

```python
from pydantic import BaseModel, field_validator

class Trade(BaseModel):
    symbol: str
    price: float

    @field_validator("symbol")          # mode="after" by default
    @classmethod
    def normalise(cls, v: str) -> str:
        return v.strip().upper()        # return value replaces the field
```

- Must be `@classmethod`. Raise `ValueError` to fail; return the (transformed) value to pass.
- Apply to multiple fields: `@field_validator("open", "close", "high", "low")`.

### mode='before' vs mode='after'

```python
@field_validator("price", mode="before")
@classmethod
def strip_commas(cls, v):             # v is raw input — could be any type
    if isinstance(v, str):
        return v.replace(",", "")     # "1,234.5" → "1234.5" before float coercion
    return v
```

| mode | `v` type | Use for |
|---|---|---|
| `"after"` (default) | declared field type | semantic checks, normalisation on the parsed value |
| `"before"` | raw input (`Any`) | cleaning/reformatting before type coercion |

---

## @model_validator

For cross-field validation or whole-model transforms.

### mode='after' — most common

```python
from pydantic import model_validator
from typing import Self

class DateRange(BaseModel):
    start: date
    end: date

    @model_validator(mode="after")
    def end_after_start(self) -> Self:
        if self.end <= self.start:
            raise ValueError("end must be after start")
        return self          # must return self
```

Receives `self` (fully constructed instance, all fields validated). Return `self`.

### mode='before' — remap raw input

```python
@model_validator(mode="before")
@classmethod
def remap_keys(cls, data: dict) -> dict:
    if "amount" in data and "qty" not in data:
        data["qty"] = data.pop("amount")   # handle legacy key
    return data
```

Receives raw `dict`; runs before any field validation. Must be `@classmethod`.

---

## Execution order

```
model_validator(before) → field coercion → field_validator(before)
  → type validation → field_validator(after) → model_validator(after)
```

---

## ValidationError

All failures are collected before raising — Pydantic reports every broken field, not just the first:

```python
try:
    Trade(symbol="", price=-1)
except ValidationError as e:
    e.errors()   # list of dicts: loc, msg, type, input
```

---

## When to use which

| Need | Tool |
|---|---|
| Simple numeric/string constraint | `Field(gt=0, min_length=1, ...)` |
| Clean/reformat one field before coercion | `@field_validator(mode="before")` |
| Validate/normalise one field after coercion | `@field_validator(mode="after")` |
| Cross-field consistency (all fields available) | `@model_validator(mode="after")` |
| Remap or merge input keys before parsing | `@model_validator(mode="before")` |

!!! tip "before vs after mental model"
    `before` means *the input has not been touched yet* — use it to accept multiple input formats. `after` means *Pydantic has already coerced and typed the value* — use it to assert semantic rules on the clean data.

!!! warning "Field order in field_validator(after)"
    `info.data` inside a `mode='after'` field validator only contains fields declared *before* the current one. For logic that needs all fields simultaneously, use `@model_validator(mode='after')`.

See [pydantic.md](pydantic.md) for the full model overview.