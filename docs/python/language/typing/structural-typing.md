---
tags:
  - typing
quiz: core
---

# Structural Typing

Two ways a type system decides "is X acceptable where T is expected?":

- **Nominal** — X must be *declared* as T (via inheritance or registration).
- **Structural** — X must have T's *shape*: the right methods and attributes, no declaration needed.

Python's runtime has always been structural (duck typing). `Protocol` (PEP 544, Python 3.8+) extends that to static analysis via [mypy](../../tooling/mypy.md).

## `Protocol`

```python
from typing import Protocol

class Serialisable(Protocol):
    def to_dict(self) -> dict[str, object]: ...

def save(obj: Serialisable) -> None:
    data = obj.to_dict()   # mypy checks structurally
```

Any class with a compatible `to_dict` method satisfies `Serialisable` — **without inheriting from it**. Third-party classes work out of the box.

Protocols can also require attributes:

```python
class HasName(Protocol):
    name: str
```

## Protocol vs ABC

| | `Protocol` | `abc.ABC` |
|--|-----------|-----------|
| Declaration required | No | Yes — must subclass |
| Third-party classes | Works | Won't unless they inherit |
| Enforcement | mypy (static) | `abstractmethod` (runtime) |
| `isinstance` | Only with `@runtime_checkable` | Yes |

!!! tip "When to reach for each"
    Use `Protocol` when accepting any object with the right shape (especially from libraries you don't control). Use `ABC` when you own the hierarchy and need to enforce implementation at construction time.

## `@runtime_checkable`

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Quackable(Protocol):
    def quack(self) -> str: ...

isinstance(obj, Quackable)   # True if obj has .quack — checks name only, not signature
```

Use sparingly — it only verifies method *existence*, not signatures.

## Verifying Protocol conformance

Two separate questions: does a class satisfy a Protocol **statically** (mypy), or **at runtime**?

### Static — assignability trick (catches signature mismatches)

```python
def _check(x: PostgresTradeRepo) -> TradeRepo:
    return x   # mypy errors here if signatures don't match
```

Put this at module level. Zero runtime cost; mypy catches missing methods *and* wrong signatures.

`assert_type` (Python 3.11+ / `typing_extensions`) is an alternative that reads more clearly:

```python
from typing import assert_type
assert_type(PostgresTradeRepo(conn), TradeRepo)  # no-op at runtime
```

### Runtime — `isinstance` with `@runtime_checkable`

```python
assert isinstance(PostgresTradeRepo(conn), TradeRepo)  # usable in pytest
```

!!! warning "isinstance with @runtime_checkable only checks attribute names, not signatures"
    A class with `def get(self, wrong_arg_name): return None` passes an `isinstance` check against a Protocol that requires `get(self, trade_id: int)`. The names match; the signatures don't. Use the assignability trick or `assert_type` (mypy) to catch signature mismatches — `isinstance` alone is insufficient.

| Technique | Catches missing methods | Catches wrong signatures | Needs mypy |
|-----------|------------------------|--------------------------|------------|
| `isinstance` (`@runtime_checkable`) | Yes | **No** | No |
| Assignability function / `assert_type` | Yes | Yes | Yes |

Use both: mypy for correctness, `isinstance` test to document intent and catch omissions.

## Protocol inheritance

```python
class Readable(Protocol):
    def read(self) -> bytes: ...

class Writable(Protocol):
    def write(self, data: bytes) -> int: ...

class ReadWritable(Readable, Writable, Protocol): ...   # include Protocol in MRO
```

!!! warning "Always include `Protocol` when inheriting protocols"
    Omitting it makes mypy treat the subclass as a regular nominal class, breaking structural checking.

## `Callable` is structural too

`Callable[[int], str]` — accepts any callable with that signature (function, lambda, `__call__` object). Structural typing working implicitly in everyday annotations.

## Mental model

> Nominal: "Is it *declared* to be the right type?"  
> Structural: "Does it *have the right shape*?"

Related: [oop.md](../objects/oop.md) for inheritance, MRO, and ABCs; [typing.md](typing.md) for `Literal` and other constructs; [mypy.md](../../tooling/mypy.md) for static checking configuration; [repository-di.md](../objects/repository-di.md) for Protocol-based dependency injection.
