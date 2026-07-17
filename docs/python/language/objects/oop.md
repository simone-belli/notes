---
tags:
  - typing
quiz: core
---

# Classes: Inheritance and ABCs

## Inheritance

- Composition (x has y) is preferred over inheritance (x is y).
- Multiple inheritance available (`class U(A, B)`). The MRO (method resolution order) determines which method is called. Check `cls.__mro__`.
- The MRO follows the C3 linearisation algorithm.
- Use `super()` to call the next class in the MRO.
- Subclassing built-in types has pitfalls — consider before doing.
- Some say only ABCs (abstract base classes) should be subclassed.

!!! note "Composition over inheritance"
    Inheritance couples the subclass to the parent's implementation, not just its interface — a change in the parent can silently break children. Reach for inheritance only when the subclass genuinely *is* a parent (and usually via an ABC); otherwise hold the other object as an attribute.

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

## Interfaces without inheritance

For duck-typed interfaces — `Protocol`, the Protocol-vs-ABC comparison, `@runtime_checkable`, and how to verify conformance — see [structural-typing.md](../typing/structural-typing.md).

See also: [data-model.md](data-model.md) for dunder methods and `@dataclass`; [repository-di.md](repository-di.md) for interface-based dependency injection.
