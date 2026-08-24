---
tags:
  - typing
quiz: detail
---

# Dataclasses

A decorator that generates boilerplate methods (`__init__`, `__repr__`, `__eq__`, …) from class-level type annotations. For classes whose job is to *hold* data.

```python
from dataclasses import dataclass

@dataclass
class Trade:
    symbol: str
    price: float
    quantity: int = 1        # defaults must follow non-defaults

t = Trade("AAPL", 190.5)
t                            # Trade(symbol='AAPL', price=190.5, quantity=1)
t == Trade("AAPL", 190.5)    # True — field-wise equality
```

!!! note "Annotations are what create fields, not assignment"
    Only names with a type annotation in the class body become fields. `x: int = 3` is a field; `x = 3` is a plain class attribute, invisible to `__init__`, `__repr__`, and `__eq__`. The annotation is never type-checked at runtime — it is only a marker (and `typing.Any` works fine if you don't care).

## Decorator parameters

`@dataclass(...)` — all keyword-only, shown with defaults:

| Parameter | Default | Effect |
|---|---|---|
| `init` | `True` | Generate `__init__` |
| `repr` | `True` | Generate `__repr__` |
| `eq` | `True` | Generate `__eq__` (tuple-of-fields comparison) |
| `order` | `False` | Generate `__lt__`, `__le__`, `__gt__`, `__ge__` |
| `frozen` | `False` | Block attribute assignment (`FrozenInstanceError`) |
| `unsafe_hash` | `False` | Force `__hash__` on a mutable dataclass |
| `match_args` | `True` | Generate `__match_args__` for positional patterns (3.10+) |
| `kw_only` | `False` | Make every field keyword-only (3.10+) |
| `slots` | `False` | Generate `__slots__` (3.10+) |
| `weakref_slot` | `False` | Add `__weakref__` to slots (3.11+) |

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class Point:
    x: float
    y: float
```

!!! warning "eq=True sets `__hash__ = None` — instances become unhashable"
    The default `@dataclass` generates `__eq__`, which per the data model kills the inherited `__hash__`. Use `frozen=True` (generates both `__eq__` and `__hash__`) for value objects you want in sets or as dict keys. `unsafe_hash=True` forces a hash on a mutable class — only safe if you guarantee no mutation after hashing. See [hash.md](hash.md).

## `field()` — per-field configuration

```python
from dataclasses import dataclass, field

@dataclass
class Order:
    items: list[str] = field(default_factory=list)   # fresh list per instance
    total: float = 0.0
    _cache: dict = field(default_factory=dict, repr=False, compare=False)
    created_by: str = field(default="system", metadata={"unit": "none"})
    line_count: int = field(init=False, default=0)   # set in __post_init__
```

| `field()` argument | Effect |
|---|---|
| `default` | Plain default value |
| `default_factory` | Zero-arg callable called per instance (mutually exclusive with `default`) |
| `init` | Include in `__init__` signature |
| `repr` | Include in `__repr__` |
| `compare` | Include in `__eq__` / ordering |
| `hash` | Include in `__hash__` (defaults to `compare`) |
| `kw_only` | Make this one field keyword-only (3.10+) |
| `metadata` | Arbitrary mapping, ignored by dataclasses; read via `fields()` |

!!! warning "Mutable defaults raise at class-creation time"
    `items: list = []` is a `ValueError`, not a shared-state bug — dataclasses detect `list`/`dict`/`set` defaults and refuse. Always use `default_factory`. Note the check is by unhashability, so a mutable *custom* class as a default slips through and is shared across instances.

## `__post_init__` and `InitVar`

`__post_init__` runs at the end of the generated `__init__` — the place for validation and derived fields.

```python
from dataclasses import dataclass, field, InitVar

@dataclass
class Price:
    amount: float
    currency: str = "USD"
    rounded: float = field(init=False)
    precision: InitVar[int] = 2          # constructor-only, not a field

    def __post_init__(self, precision: int) -> None:
        if self.amount < 0:
            raise ValueError("amount must be non-negative")
        self.rounded = round(self.amount, precision)
```

- `InitVar[T]` fields are passed to `__init__` and forwarded to `__post_init__`, but are not stored, compared, or shown in `__repr__`.
- `ClassVar[T]` annotations are skipped entirely — a normal class attribute, shared by all instances.
- Under `frozen=True`, assign in `__post_init__` via `object.__setattr__(self, "rounded", ...)`.

## Helper functions

```python
from dataclasses import asdict, astuple, fields, replace, is_dataclass, MISSING

asdict(t)                    # {'symbol': 'AAPL', ...} — recurses into nested dataclasses/list/dict
astuple(t)                   # ('AAPL', 190.5, 1)
replace(t, price=191.0)      # new instance, other fields copied (re-runs __init__/__post_init__)
fields(Trade)                # tuple of Field objects: .name, .type, .default, .metadata
is_dataclass(t)              # True for both the class and its instances
f.default is MISSING         # sentinel for "no default"
```

`asdict` deep-copies — for a shallow one-level mapping use `{f.name: getattr(t, f.name) for f in fields(t)}`.

## Ordering

`order=True` compares the tuple of all `compare=True` fields, in declaration order:

```python
@dataclass(order=True)
class Version:
    major: int
    minor: int

sorted([Version(1, 9), Version(1, 2)])   # [Version(1, 2), Version(1, 9)]
```

Comparison with a different class returns `NotImplemented` → `TypeError`. To sort by a computed key, add a leading `sort_index: float = field(init=False, repr=False)` set in `__post_init__`.

## Inheritance

Fields are merged in reverse Method Resolution Order (MRO): base fields first, then the subclass's. Redeclaring a name overrides it in place, keeping its original position.

```python
@dataclass
class Base:
    a: int = 0

@dataclass
class Child(Base):
    b: str          # TypeError: non-default argument 'b' follows default argument 'a'
```

Fixes: give `b` a default, or use `kw_only=True` (which lifts the ordering restriction entirely).

## Gotchas

- `x = 3` without an annotation is not a field.
- `frozen` is shallow — a frozen dataclass holding a `list` still lets you mutate that list.
- A non-frozen dataclass cannot inherit from a frozen one, and vice versa.
- `slots=True` returns a *new class object*; decorators or references captured before it won't match, and it breaks `default_factory` closures over the old class.
- `asdict()` on a class with non-dataclass, non-container fields just returns the object (deep-copied), not a serialisable form.

## Related

- [data-model.md](data-model.md) — the dunder methods dataclasses generate for you
- [hash.md](hash.md) — the `__eq__`/`__hash__` contract behind `frozen=True`
- [attribute-lookup.md](attribute-lookup.md) — what `__slots__` does to attribute storage
- [match.md](../runtime/match.md) — `__match_args__` and positional patterns
- [pydantic.md](../../libraries/pydantic/pydantic.md) — runtime validation at system boundaries vs. dataclasses for internal models
