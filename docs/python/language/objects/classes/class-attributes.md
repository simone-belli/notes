---
tags:
  - typing
---

# Class attributes

A name assigned in the **class body** belongs to the class, not to any instance — one object, shared by every instance. That is how you give a class a fixed parameter: `unit` below exists once, created when the `class` statement runs.

```python
class Circle:
    unit = "cm"          # class attribute — shared

    def __init__(self, r):
        self.r = r       # instance attribute — one per object

a, b = Circle(1), Circle(2)
a.unit, b.unit           # ('cm', 'cm')
Circle.unit              # 'cm' — reachable on the class itself
a.__dict__               # {'r': 1} — 'unit' is not in here
```

!!! note "Reads find the class, writes go to the instance"
    `a.unit` falls back to the class because that is the [attribute lookup order](attribute-lookup.md). But `a.unit = "mm"` never touches the class — it inserts a key into `a.__dict__` that *shadows* the shared value for that one object. To change it for everyone, assign on the class: `Circle.unit = "mm"`.

```python
a.unit = "mm"
a.unit, b.unit           # ('mm', 'cm') — a is shadowing
del a.unit               # drop the shadow
a.unit                   # 'cm'
```

## Declaring the intent: `ClassVar` and `Final`

Annotations mark the name as deliberately class-level rather than a forgotten instance field. Both are checker-only — no runtime effect.

```python
from typing import ClassVar, Final

class Circle:
    unit: ClassVar[str] = "cm"         # mypy: error on self.unit = "mm"
    TAU: Final = 6.283185307179586     # mypy: error on any reassignment
```

- `ClassVar[T]` — forbids assignment through an instance; the class attribute stays writable as `Circle.unit`.
- `Final` — forbids reassignment anywhere, including on the class. Use it for a true constant, with `UPPER_CASE` naming.

In a [dataclass](../dataclasses.md), `ClassVar` is the only annotated way to add a shared value without it becoming a field:

```python
from dataclasses import dataclass
from typing import ClassVar

@dataclass
class Circle:
    r: float
    unit: ClassVar[str] = "cm"   # skipped by __init__, __repr__, __eq__

Circle(1.0)                      # Circle(r=1.0) — no unit argument
```

## Keep the shared value immutable

!!! warning "A mutable class attribute is shared mutable state"
    One `list` for the whole class means one instance's `append` is visible from all the others. `.append` *mutates* the shared object where `=` would have shadowed it — the same [rebind vs mutate](../mutation.md) distinction.

```python
class Bad:
    seen = []            # ONE list for every instance

Bad().seen.append(1)
Bad().seen               # [1] — set by a different instance
```

Per-instance mutable state belongs in `__init__` (`self.seen = []`), or in a dataclass `field(default_factory=list)`. Restrict class attributes to `str`, `int`, `tuple`, `frozenset`.

## Making it genuinely read-only

Nothing stops `Circle.unit = "mm"` at runtime; the annotation plus naming convention is the usual whole enforcement. When the value must be unassignable:

- **Module-level constant** (`UNIT = "cm"`) — simplest when the value isn't conceptually part of the class.
- **`@property` with no setter** returning the constant — raises `AttributeError` on assignment, but costs a call per read and isn't reachable as `Circle.unit`.
- **`enum.Enum`** — when the fixed value is one of a closed set of named choices; members can't be rebound.
- **`__slots__` omitting the name** — leaves the class attribute readable while making the instance shadow impossible, since there is nowhere to store it.

## Related

- [Attribute lookup protocol](attribute-lookup.md) — the full `obj.x` resolution order, descriptors, `__slots__`
- [Class introspection](introspection.md) — checking at runtime whether a name is a class attribute, an instance attribute, or only an annotation
- [Dataclasses](../dataclasses.md) — `ClassVar`, `field()`, `default_factory`
- [The Data Model and Pythonic Objects](data-model.md) — `@classmethod` for class-level state and registries
