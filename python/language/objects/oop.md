# Classes: Inheritance and Interfaces

## Inheritance

- Composition (x has y) is preferred over inheritance (x is y).
- Multiple inheritance available (`class U(A, B)`). The MRO (method resolution order) determines which method is called. Check `cls.__mro__`.
- The MRO follows the C3 linearisation algorithm.
- Use `super()` to call the next class in the MRO.
- Subclassing built-in types has pitfalls — consider before doing.
- Some say only ABCs (abstract base classes) should be subclassed.

## Abstract Base Classes (ABCs)

```python
from abc import ABC, abstractmethod

class Instrument(ABC):

    @property
    @abstractmethod
    def symbol(self) -> str: ...

    @abstractmethod
    def price(self) -> Decimal: ...
```

- ABCs use **nominal typing**: a class must explicitly inherit from the base class.
- Subclasses that don't implement all abstract methods cannot be instantiated.
- Better for frameworks, plugins, and strict class designs.
- ABCs are better when the base class provides shared implementation.

## Protocols

- `Protocol` defines an interface based on object structure, from `typing`: `from typing import Protocol`.
- A class satisfies a protocol if it has the required methods/attributes — no explicit inheritance needed.
- This is called **structural typing**, matching Python's duck typing idea.
- Protocols are mainly useful for static type checkers like `[mypy](../../tooling/mypy.md)`.
- By default, protocols do not enforce behaviour at runtime.
- `@runtime_checkable` allows limited `isinstance()` checks.

## Protocols vs ABCs


|                      | ABC                               | Protocol                        |
| -------------------- | --------------------------------- | ------------------------------- |
| Typing               | Nominal                           | Structural                      |
| Requires inheritance | Yes                               | No                              |
| Runtime enforcement  | Yes                               | Optional (`@runtime_checkable`) |
| Best for             | Frameworks, shared implementation | Flexible duck typing            |


- ABC: "you belong to this family."
- Protocol: "you behave in the required way."
- In modern Python, protocols are often preferred for lightweight interfaces.

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
from typing import runtime_checkable

@runtime_checkable
class TradeRepo(Protocol):
    def get(self, trade_id: int) -> Trade: ...
    def save(self, trade: Trade) -> None: ...

assert isinstance(PostgresTradeRepo(conn), TradeRepo)  # usable in pytest
```

**Critical limitation**: `isinstance` only checks that the attribute *names* exist — not signatures. A class with `def get(self, x): return "nonsense"` passes.

| Technique | Catches missing methods | Catches wrong signatures | Needs mypy |
|-----------|------------------------|--------------------------|------------|
| `isinstance` (`@runtime_checkable`) | Yes | **No** | No |
| Assignability function / `assert_type` | Yes | Yes | Yes |

Use both: mypy for correctness, `isinstance` test to document intent and catch omissions.

See also: [data-model.md](data-model.md) for dunder methods and `@dataclass`; [repository-di.md](repository-di.md) for Protocol-based dependency injection.