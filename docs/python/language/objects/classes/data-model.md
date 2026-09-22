---
quiz: core
---

# The Data Model and Pythonic Objects

## The Data Model

- The key API of the Python language is the Data Model.
- It is a class framework in which classes have special methods (dunder methods).
- The advantage of dunder methods is uniformity and the ability to apply built-in functions to them.
- Typical examples: `__init__`, `__len__`, [`__getitem__`](../../typing/subscriptable.md), `__repr__`, `__hash__` and arithmetic operators.
- Emulating sequences is one of the most common uses.

## `__new__` vs `__init__`

`__new__` **creates** the instance; `__init__` only **initializes** one that already exists. Calling `C(...)` runs `cls.__new__(cls, ...)` first, then calls `obj.__init__(...)` — but only if `__new__` returned an instance of `cls` (or a subclass). Return something else (or `None`), and `__init__` never runs.

```python
class C:
    def __new__(cls, *args, **kwargs):
        return super().__new__(cls)   # actually allocates the object; cls, not self — no instance exists yet
    def __init__(self, *args, **kwargs):
        ...   # configures the already-created instance
```

!!! note "Why bother overriding `__new__` at all"
    Because it decides *whether* an instance is created and *of what type* — `__init__` can't do either. Four cases where that matters: subclassing an immutable built-in (`int`/`str`/`tuple` — the value must be fixed before `__init__` could ever run); a singleton (`__new__` returns a cached instance instead of allocating a new one); a "virtual constructor" that dispatches to a different class based on arguments; and `type.__new__` itself — the same protocol one level up, used to construct class objects from a metaclass (see [class-creation.md](class-creation.md)).

```python
class PositiveInt(int):
    def __new__(cls, value):
        if value <= 0:
            raise ValueError("must be positive")
        return super().__new__(cls, value)   # value fixed here — too late once __init__ would run
```

A `@classmethod` alternative constructor (below) still goes through the full `__new__` → `__init__` cycle — it's a named wrapper around the normal path. Overriding `__new__` changes that path itself, for every call to `C(...)`.

## Pythonic Objects

- String/bytes representation: `__repr__`, `__str__`, `__format__`, `__bytes__`
- Use `__eq__` and `__hash__` to support equality testing and use in sets/dicts.
- `__call__` makes an object callable (i.e., `obj(x)`) — see [callable.md](../../typing/callable.md).
- Decorators `@classmethod` and `@staticmethod` change what the method is bound to — see [Method types](#method-types) below.
- Implement `__format__` that parses `format_spec` to use:
  - `format(obj, format_spec)`
  - `'1 BRL = {rate:0.2f} USD'.format(rate=brl)`
  - `f'1 USD = {1 / brl:0.2f} BRL'`
- Make objects immutable by making attributes private with `self.__x`, then define a getter with `@property`.
- Declare the class attribute `__slots__` to save memory. See [attribute-lookup.md](attribute-lookup.md) for how `@property` and `__slots__` actually work — both are special cases of the descriptor protocol behind `obj.x`.
- Define the class attribute `typecode`, which an instance can override.

## Method types

Three ways to attach a function to a class. They differ only in what Python passes as the implicit first argument:

| Decorator | Implicit first argument | Called on | Can reach |
|---|---|---|---|
| *(none)* | `self` — the instance | instance | instance state **and** class state |
| `@classmethod` | `cls` — the class it was reached through | class or instance | class state only |
| `@staticmethod` | nothing | class or instance | neither |

The choice follows from what the body actually touches: it uses `self` → instance method; it needs the class, to construct it or to read a class attribute polymorphically → `@classmethod`; it needs neither → `@staticmethod`.

### @classmethod

Receives the class as first argument (`cls`) instead of the instance. Called on the class or any instance.

```python
class Trade:
    def __init__(self, symbol: str, price: float, side: str):
        self.symbol = symbol
        self.price = price
        self.side = side

    @classmethod
    def from_dict(cls, data: dict) -> "Trade":       # alternative constructor
        return cls(data["symbol"], data["price"], data["side"])

    @classmethod
    def from_string(cls, s: str) -> "Trade":         # "AAPL:182.5:BUY"
        symbol, price, side = s.split(":")
        return cls(symbol, float(price), side)

trade = Trade.from_dict({"symbol": "AAPL", "price": 182.5, "side": "BUY"})
```

- Main use: **alternative constructors** — several named ways to build an instance from different input formats, since `__init__` can only have one signature.
- Writing `cls(...)` rather than `Trade(...)` is what makes them inheritable: `SpreadTrade.from_dict(...)` returns a `SpreadTrade`.
- Also used for class-level state and registries — anything whose receiver should be the class, such as a counter in a class attribute or a `register()` that populates a lookup table on the class.
- Required by Pydantic for [`@field_validator`](../../../libraries/pydantic/pydantic-validators.md).

### @staticmethod

Receives no implicit argument at all — a plain function that happens to live in the class namespace.

```python
class Trade:
    ...

    @staticmethod
    def is_valid_side(side: str) -> bool:
        return side in {"BUY", "SELL"}

Trade.is_valid_side("BUY")        # True — no instance, no cls
```

- Use it for a helper that belongs to the class's vocabulary but needs no state: validating an input, a unit conversion, a small pure computation.
- It is the weakest of the three. A module-level function does the same work and is easier to import and test, so reach for `@staticmethod` only when grouping under the class aids discoverability, or when subclasses should be able to override the helper.
- The other genuine use is storing a function as a class attribute. A bare `callback = log` at class level is turned into a bound method on access (functions are descriptors), so wrap it: `callback = staticmethod(log)`. See [callbacks.md](../../functional/callbacks.md).

### Binding mechanics

`classmethod` and `staticmethod` are not interpreter magic — both are ordinary descriptors that customise `__get__`, the same hook that turns a plain function into a bound method. `classmethod.__get__` binds to the owning class, `staticmethod.__get__` binds to nothing and hands back the raw function. See [attribute-lookup.md](attribute-lookup.md) for the full lookup protocol.

!!! warning "Only `@classmethod` adapts to the subclass"
    `Sub.from_dict(...)` sets `cls is Sub`, so the alternative constructor builds a `Sub` without being overridden. A `@staticmethod` receives nothing and cannot tell which class it was reached through — if a static helper needs to branch on the class, it is a classmethod in disguise.

Two version details worth knowing: `staticmethod` objects became directly callable in Python 3.10 (before that, `Trade.__dict__["is_valid_side"]("BUY")` raised `TypeError`), and stacking `@classmethod` on top of `@property` to make a "class property" — briefly supported in 3.9 — was deprecated in 3.11 and removed in 3.13. When combining either decorator with `@abstractmethod` from an abstract base class, put `@abstractmethod` innermost, directly above the `def`.

## `@dataclass`

!!! tip "Use frozen=True to get hashability and immutability for free"
    `@dataclass` alone generates `__eq__` but sets `__hash__ = None`, making instances unhashable (can't be used in sets or as dict keys). `@dataclass(frozen=True)` also generates `__hash__` and prevents attribute mutation — the right default for value objects like `Trade`, `Point`, or `Price`.

- `@dataclass` is a decorator from the `dataclasses` module.
- It automatically generates boilerplate methods like `__init__` and `__repr__`.
- Mainly used for classes that store data.
- Fields are defined using type hints.
- `@dataclass(frozen=True)` makes instances immutable and adds `__hash__`.
- `__post_init__`: validation runs after `__init__`.

```python
from dataclasses import dataclass

@dataclass
class Trade:
    symbol: str
    price: float
```

See [dataclasses.md](../dataclasses.md) for the full cheat sheet: decorator parameters, `field()`, `InitVar`, and helper functions.

See also: [oop.md](oop.md) for inheritance and ABCs; [structural-typing.md](../../typing/structural-typing.md) for Protocols.