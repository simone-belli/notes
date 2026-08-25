---
tags:
  - typing
---

# Callable

"Callable" names two connected things: a **runtime protocol** (an object defines `__call__`, so `obj(...)` works) and a **type annotation** (`Callable[[int], str]`, describing the shape of a call).

## The runtime protocol

`f(x)` is not syntax reserved for functions — the interpreter looks up `__call__` on `type(f)` and calls that. Anything with `__call__` is callable:

- `def` functions and lambdas
- bound methods
- **classes** — `MyClass(3)` runs `type.__call__`, which calls `__new__` then `__init__`
- `functools.partial` objects ([functools](../functional/functools.md))
- instances of classes defining `__call__`

```python
callable(len)        # True
callable(int)        # True — classes are callable
callable([].append)  # True — bound method
callable("hi")       # False
```

`callable(x)` only answers "can this be called at all" — it says nothing about the signature.

### Callable instances — functions with state

```python
class Counter:
    def __init__(self) -> None:
        self.count = 0

    def __call__(self, item: str) -> str:
        self.count += 1
        return f"{self.count}: {item}"

tag = Counter()
tag("a")     # '1: a'
tag.count    # 1 — state is a normal attribute
```

Equivalent to a [closure](../runtime/scopes.md#closures), but the state is inspectable, picklable, and can be joined by other methods. Closure for throwaway state; callable class when the state is part of the API. See [`__call__` in the data model](../objects/classes/data-model.md).

!!! warning "A function stored as a class attribute becomes a method"
    Python functions are descriptors, so `callback = log` at class level binds `self` as the first argument on access. Assign it in `__init__` (`self.callback = log`) or wrap it in `staticmethod(log)`.

## The annotation

```python
from collections.abc import Callable

def apply_twice(f: Callable[[int], int], x: int) -> int:
    return f(f(x))
```

Syntax is `Callable[[params...], return]`:

```python
Callable[[], None]          # no arguments, returns None
Callable[[int, str], bool]  # two positional arguments
Callable[..., str]          # any arguments, returns str
```

The return type is never optional — `Callable[[int]]` is invalid. `...` (a literal `Ellipsis`) opts out of parameter checking; prefer an explicit list when the signature is known.

Import from `collections.abc`: `typing.Callable` has been deprecated since Python 3.9 (PEP 585). `collections.abc.Callable` also works unsubscripted with `isinstance`, but a subscripted form raises `TypeError` — signatures are checkable only statically.

### Variance

`Callable` is **contravariant in parameters**, **covariant in the return type**: `Callable[[Animal], Dog]` can substitute for `Callable[[Dog], Animal]`, not the other way round.

!!! tip "Substitution rule"
    A replacement callable must be **at least as permissive** about what goes in and **at least as specific** about what comes out.

### What `Callable` cannot express

Positional parameters only — no keyword-only arguments, defaults, `*args`/`**kwargs`, or overloads. For those, use a **callback Protocol** (see [structural typing](structural-typing.md)):

```python
from typing import Protocol

class Formatter(Protocol):
    def __call__(self, value: float, *, precision: int = 2) -> str: ...
```

Parameter names now matter, since callers can pass them by keyword.

### `ParamSpec` — forwarding a signature through a decorator

`Callable[..., Any]` erases the wrapped signature of a [decorated function](../functional/functools.md). `ParamSpec` (Python 3.10, PEP 612) captures the whole parameter list as one unit:

```python
from collections.abc import Callable
from typing import ParamSpec, TypeVar
import functools

P = ParamSpec("P")
R = TypeVar("R")

def logged(fn: Callable[P, R]) -> Callable[P, R]:
    @functools.wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        print(f"calling {fn.__name__}")
        return fn(*args, **kwargs)
    return wrapper

@logged
def add(a: int, b: int) -> int: ...

add("x", 2)   # mypy error — signature survived the decorator
```

`P.args`/`P.kwargs` are the only legal spelling inside the wrapper. `Concatenate[Connection, P]` covers decorators that supply a leading argument the caller doesn't pass. Python 3.12 allows the inline form `def logged[**P, R](fn: Callable[P, R]) -> Callable[P, R]`.

## Choosing a form

| Need | Use |
|------|-----|
| Simple positional signature | `Callable[[A, B], R]` |
| Parameters don't matter | `Callable[..., R]` |
| Keyword or default arguments | callback `Protocol` with `__call__` |
| Preserve a signature through a decorator | `ParamSpec` |
| Callable *plus* other attributes | `Protocol` with `__call__` and the rest |

Typical uses: callbacks (`on_error: Callable[[Exception], None]`), strategy injection, sort keys, `default_factory: Callable[[], T]`, and command registries (`dict[str, Callable[..., Command]]`).

Related: [structural typing](structural-typing.md) for Protocols; [typing module](typing.md) for `Literal`, `overload`, `cast`; [subscriptable types](subscriptable.md) for how `Callable[...]` is built; [mypy](../../tooling/mypy.md) for enforcement.
