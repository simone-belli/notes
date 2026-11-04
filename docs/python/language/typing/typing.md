---
tags:
  - typing
quiz: core
---

# typing module — selected constructs

Key types from `typing` (and `typing_extensions`) that go beyond basic annotations — see [Type Hints](type-hints.md) for unions, generics, `TypedDict`, and the module overview. Enforced by [mypy](../../tooling/mypy.md) and [Pydantic](../../libraries/pydantic/pydantic.md) at parse time; ignored by the Python runtime.

---

## `Literal` — restrict to specific values

Narrows a type to a fixed set of constants rather than the broad base type.

```python
from typing import Literal

Side = Literal['BUY', 'SELL']

def place_order(side: Side) -> None: ...

place_order('BUY')    # ok
place_order('hold')   # mypy error
```

Allowed value types: `str`, `int`, `bool`, `bytes`, `None`, Enum members. Not variables or mutable types.

### Subtype direction

!!! warning "A plain str variable fails assignment to a Literal type"
    `Literal['BUY']` is a subtype of `str`, but `str` is *not* a subtype of `Literal['BUY', 'SELL']`. This means passing a `str` variable (even one that happens to hold `'BUY'`) to a `Literal`-typed parameter is a mypy error. You must either narrow the variable first (e.g. via a branch or `assert`) or use a `Literal` annotation at the assignment site.

`Literal['BUY']` is a **subtype** of `str` — narrowing is always safe.  
`str` is **not** a subtype of `Literal['BUY']` — a bare `str` variable could be anything.

```python
x: str = 'BUY'
place_order(x)   # mypy error: str is not assignable to Literal['BUY', 'SELL']
```

### Type narrowing in branches

```python
def process(side: Literal['BUY', 'SELL']) -> None:
    if side == 'BUY':
        ...  # checker knows: side is Literal['BUY']
    else:
        ...  # checker knows: side is Literal['SELL']
```

### Overloads — different return types per literal argument

```python
from typing import overload

@overload
def parse(raw: str, mode: Literal['int']) -> int: ...
@overload
def parse(raw: str, mode: Literal['float']) -> float: ...
def parse(raw: str, mode: str) -> int | float:
    return int(raw) if mode == 'int' else float(raw)

x = parse("42", "int")     # x: int
y = parse("3.14", "float") # y: float
```

### Runtime introspection

```python
from typing import get_args

get_args(Side)  # ('BUY', 'SELL')

# Manual validation without Pydantic:
if value not in get_args(Side):
    raise ValueError(f"invalid side: {value!r}")
```

### `Literal` vs `Enum`

| | `Literal` | `Enum` |
|--|-----------|--------|
| Runtime type | plain `str`/`int` | `Enum` instance |
| Methods | none | can add |
| Pydantic JSON | natural | needs `.value` |
| Use when | static valid-value set, no logic | need behaviour or identity |

### `TypeAlias`

```python
from typing import TypeAlias
Side: TypeAlias = Literal['BUY', 'SELL']  # explicit alias (Python 3.10+)
```

Python 3.12 adds `type Side = Literal['BUY', 'SELL']` as a cleaner alternative.

### Version

Introduced in Python 3.8 (Python Enhancement Proposal (PEP) 586).

---

## `cast` — override the checker, not the runtime

`cast(Type, value)` tells the type checker "treat this as `Type`" with zero runtime effect — no `isinstance` check, no conversion. It's `return value` under the hood.

```python
from typing import cast

raw: dict[str, object] = get_config()
port = cast(int, raw["port"])  # checker now treats port as int
```

Use it when a checker can't infer a type you know to be true (e.g. after `json.loads()`, or a loose library stub) — not to silence errors you don't understand.

!!! warning "No runtime safety"
    If the value isn't actually `Type`, `cast` won't catch it — the bug surfaces later, elsewhere. Prefer `assert isinstance(x, T)` when you want the check enforced at runtime; reach for `cast` when the type is unrepresentable at runtime (generics like `list[int]`, Protocols) or verification is genuinely too costly.

---

## `Final` and `ClassVar`

```python
from typing import ClassVar, Final, final

MAX_RETRIES: Final = 3          # rebinding is a checker error

class Config:
    registry: ClassVar[dict[str, "Config"]] = {}   # class attribute, not a field

@final
class Leaf: ...                 # subclassing is a checker error
```

- `Final` and `@final` are checker-only; the runtime still lets you rebind or subclass.
- [Dataclasses](../objects/dataclasses.md) skip `ClassVar` annotations when generating fields.

---

## `Annotated` — a type plus metadata

`Annotated[T, *meta]` is `T` to a checker; the extra arguments are opaque metadata that runtime libraries read.

```python
from typing import Annotated
from pydantic import BaseModel, Field

class Order(BaseModel):
    qty: Annotated[int, Field(gt=0)]   # checker sees int; Pydantic enforces > 0
```

FastAPI uses the same pattern for `Annotated[int, Query(ge=1)]` and `Annotated[Session, Depends(get_db)]`.

---

## `NewType` — same runtime type, distinct static type

```python
from typing import NewType

UserId = NewType("UserId", int)
OrderId = NewType("OrderId", int)

def load_user(uid: UserId) -> None: ...

load_user(UserId(5))    # ok
load_user(OrderId(5))   # checker error
UserId(5) == 5          # True — at runtime it's just the int
```

- Cheaper than a wrapper class: no runtime cost and no new behaviour.
- Use a real class (or `Annotated` with validation) when the value needs checking, not just labelling.

---

## `Self` — the type of the current class

```python
from typing import Self

class Builder:
    def with_name(self, name: str) -> Self:
        self.name = name
        return self

class HtmlBuilder(Builder): ...

HtmlBuilder().with_name("x")   # HtmlBuilder, not Builder
```

Use it for fluent methods, `copy()`, and `@classmethod` alternative constructors. Python 3.11+ (earlier via `typing_extensions`).

---

## `Never` and `assert_never` — exhaustiveness

`Never` is the bottom type: no value has it. A function returning `Never` (or the older spelling `NoReturn`) always raises or never returns.

```python
from enum import Enum
from typing import assert_never

class Side(Enum):
    BUY = "buy"
    SELL = "sell"

def sign(side: Side) -> int:
    match side:
        case Side.BUY:
            return 1
        case Side.SELL:
            return -1
        case _:
            assert_never(side)   # error here if a new Side member is unhandled
```

!!! tip "Let the checker prove a `match` is complete"
    After all cases are handled, the checker narrows `side` to `Never`, so `assert_never(side)` type-checks. Add `Side.HOLD` without a branch and `side` is `Literal[Side.HOLD]` there — a checker error at exactly the spot that needs updating. See [match](../runtime/match.md).

---

## `TypeIs` — user-defined narrowing

A function returning `TypeIs[T]` tells the checker that a `True` result means the argument is `T`.

```python
from typing import TypeIs

def is_str(x: object) -> TypeIs[str]:
    return isinstance(x, str)

def describe(v: str | int) -> str:
    if is_str(v):
        return v.upper()      # v: str
    return str(v + 1)         # v: int — narrowed in the False branch too
```

- `TypeIs` (3.13, PEP 742) narrows in **both** branches and requires `T` to be a subtype of the input type.
- `TypeGuard` (3.10) narrows only the `True` branch and allows unrelated types; prefer `TypeIs` unless you need that.
- The checker trusts your function body — a wrong implementation is an unchecked lie, like [`cast`](#cast-override-the-checker-not-the-runtime).
