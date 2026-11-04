---
tags:
  - typing
---

# Type Hints

`typing` is the standard-library module that supplies the vocabulary for type hints — the names you need when a plain class can't say what you mean: "an `int` or `None`", "the same type I was given", "a dict with exactly these keys". Python itself **never enforces** them.

## Annotations are metadata

```python
def double(x: int) -> int:
    return x * 2

double("ab")              # 'abab' — no error
double.__annotations__    # {'x': <class 'int'>, 'return': <class 'int'>}
```

Three kinds of consumer read the stored hints:

- **Static checkers** ([mypy](../../tooling/mypy.md), pyright) — read the source without running it and report inconsistencies.
- **Runtime libraries** ([Pydantic](../../libraries/pydantic/pydantic.md), FastAPI, [dataclasses](../objects/dataclasses.md)) — call `typing.get_type_hints()` and validate, coerce, or generate schemas from them.
- **Editors** — completion, hover docs, refactoring.

The system is **gradual**: unannotated code is implicitly `Any`, so types can be added one function at a time.

!!! note "Claims, checks, and an indifferent runtime"
    An annotation is a claim. A checker verifies the claims are *consistent* with each other; the interpreter ignores them unless a library opts in. A wrong hint is never a runtime error — it's a lie the checker may or may not catch.

## Modern spellings

Each Python release has moved syntax out of `typing` and into the language, each change specified by a Python Enhancement Proposal (PEP). On 3.10+ write:

| Old (`typing`) | Modern | Since |
|---|---|---|
| `List[int]`, `Dict[str, int]` | `list[int]`, `dict[str, int]` | 3.9 (PEP 585) |
| `typing.Iterable`, `typing.Mapping` | `collections.abc.Iterable`, `Mapping` | 3.9 |
| `Union[A, B]`, `Optional[A]` | `A \| B`, `A \| None` | 3.10 (PEP 604) |
| `T = TypeVar("T")` | `def f[T](...)`, `class C[T]:` | 3.12 (PEP 695) |
| `X: TypeAlias = ...` | `type X = ...` | 3.12 |
| `"Node"` (quoted forward ref) | `Node` | 3.14 (PEP 649) |

The capitalised aliases still work but are deprecated; [Ruff](../../tooling/ruff.md)'s `UP` rules rewrite them. The `typing_extensions` package backports new constructs to older interpreters.

Reach into `typing` only for **special forms** with no builtin spelling — `Any`, `Literal`, `Protocol`, `TypedDict`, `Final`, `Self`, and so on.

## Unions and narrowing

```python
def find(user_id: int) -> User | None: ...

u = find(3)
u.name              # checker error: None has no attribute "name"
if u is not None:
    u.name          # ok — narrowed to User
```

- Forcing `None` to be handled is the single most valuable everyday check.
- **Narrowing** constructs: `isinstance`, `is None`, `==` against a literal, early `return`/`raise`, `match`, and [`TypeIs` functions](typing.md#typeis-user-defined-narrowing).

!!! warning "`Optional` doesn't mean optional"
    `Optional[X]` (= `X | None`) means "may be `None`", not "may be omitted". A parameter is omittable only if it has a default: `def f(x: int | None)` is still required; `def f(x: int | None = None)` is not.

## `Any` vs `object`

Both accept every value, in opposite ways:

- `Any` — the checker stops checking: any attribute, any call, assignable anywhere. It's contagious: `y = any_value.foo()` makes `y` `Any` too.
- `object` — the top type: only operations every object supports are allowed until you narrow with `isinstance`.

Write `object` for "accept anything and inspect it"; keep `Any` for untyped boundaries you can't describe.

## Abstract parameters, concrete returns

```python
from collections.abc import Iterable, Mapping

def total(prices: Iterable[float]) -> float:       # list, tuple, generator, set…
    return sum(prices)

def scores(table: Mapping[str, int]) -> list[int]:  # read-only: no table[k] = v
    return sorted(table.values())
```

- Name the smallest interface the parameter needs — it accepts more callers and documents that you don't mutate it.
- `list` is **invariant** (`list[int]` is not a `list[float]`, since you could append a float); read-only `Sequence` is **covariant**, so `Sequence[int]` is accepted where `Sequence[float]` is expected. See [Callable](callable.md) for variance.

## Generics

A type variable **links** types across a signature: whatever comes in is what goes out.

```python
from collections.abc import Sequence

def first[T](xs: Sequence[T]) -> T:     # 3.12+
    return xs[0]

first([1, 2])    # int
first(["a"])     # str
```

- **Bound**: `def biggest[T: float](xs: list[T]) -> T` — `T` is any subtype of `float`.
- **Constraints**: `def concat[S: (str, bytes)](a: S, b: S) -> S` — exactly one of the listed types, the same for both arguments.
- **Generic class**: `class Stack[T]:` with methods using `T`; instantiate as `Stack[int]()`.
- Pre-3.12: `T = TypeVar("T")` plus `Generic[T]` — see [Subscriptable Types](subscriptable.md).
- `ParamSpec` captures a whole parameter list for signature-preserving decorators ([Callable](callable.md)); `TypeVarTuple` captures a variable number of types.

## `TypedDict` and `NamedTuple`

`TypedDict` types the keys of data that *is* a dict at runtime — JSON, config:

```python
from typing import NotRequired, TypedDict

class Movie(TypedDict):
    title: str
    year: int
    rating: NotRequired[float]

m: Movie = {"title": "Heat", "year": 1995}
m["yaer"]     # checker error: no such key
```

- Still a plain `dict` at runtime — no validation, no methods. For data you own, prefer a dataclass or Pydantic model.
- `NotRequired` / `Required` (3.11) mark per-key optionality; `ReadOnly` (3.13) forbids assignment.

`NamedTuple` is a real class — an immutable tuple subclass with named, typed fields:

```python
from typing import NamedTuple

class Point(NamedTuple):
    x: float
    y: float = 0.0

Point(1.0).y    # 0.0
```

## `TYPE_CHECKING` and forward references

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:            # False at runtime, True for checkers
    from .models import Order

def ship(order: Order) -> None: ...
```

- Imports under the guard exist only for the checker — breaks [circular imports](../runtime/import-system.md) and keeps heavy imports off the startup path.
- Before 3.14 such names needed quotes (`"Order"`) or `from __future__ import annotations`; from 3.14 annotations are evaluated lazily, so the bare name works.

## Reading hints at runtime

```python
from typing import Literal, get_args, get_origin, get_type_hints

get_type_hints(double)            # resolves strings / forward refs to real objects
get_origin(list[int])             # list
get_args(dict[str, int])          # (str, int)
get_args(Literal["a", "b"])       # ('a', 'b')
```

- `get_type_hints` strips `Annotated` metadata unless `include_extras=True`.
- On 3.14+, prefer `annotationlib.get_annotations(obj)` over reading `__annotations__` directly.

!!! tip "Where the value comes from"
    Most of typing's payoff is three things: `| None` forcing `None`-handling, precise parameter types catching wrong arguments, and generics carrying types through helpers. Get those right before reaching for the exotic forms.

## Related

- [typing module — selected constructs](typing.md) — `Literal`, `overload`, `cast`, `Final`, `Annotated`, `NewType`, `Self`, `Never`, `TypeIs`
- [Structural Typing](structural-typing.md) — `Protocol`
- [Callable](callable.md) — `Callable`, variance, `ParamSpec`
