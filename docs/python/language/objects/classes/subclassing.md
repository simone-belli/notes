---
tags:
  - design-patterns
  - typing
---

# Subclassing

`class Child(Parent)` makes `Child` inherit every attribute and method the parent defines, and lets it replace any of them. The easy part is writing the subclass; the work is making it *cooperate* with the parent instead of silently replacing half of it.

```python
class Account:
    def __init__(self, balance: float) -> None:
        self.balance = balance

    def describe(self) -> str:
        return f"balance={self.balance}"

class Savings(Account):
    def __init__(self, balance: float, rate: float) -> None:
        super().__init__(balance)      # extend: run the parent's work first
        self.rate = rate

    def describe(self) -> str:
        return f"{super().describe()} rate={self.rate}"
```

- **Override** = redefine the name in the subclass. Nothing declares intent; a typo creates a new method rather than an error.
- **Extend** = override *and* call `super()`, so the parent's version still runs.
- Attribute lookup walks the subclass first, then its bases — see [attribute-lookup.md](attribute-lookup.md).

## `super()` is the *next* class, not the parent

`super()` returns a proxy that resumes the attribute search at the class *after* the current one in the method resolution order (MRO) of `type(self)` — which, under multiple inheritance, is often a sibling the author never named.

```python
class A:
    def go(self): return "A"

class B(A):
    def go(self): return "B -> " + super().go()

class C(A):
    def go(self): return "C -> " + super().go()

class D(B, C): pass

D().go()            # 'B -> C -> A'  — B's super() reached C, not A
D.__mro__           # (D, B, C, A, object)
```

- Zero-argument `super()` works only inside a method body: the compiler stores the defining class in a `__class__` closure cell and pairs it with the first positional argument. A function attached to a class *after* creation, or a nested helper that doesn't take `self`, must spell it out as `super(B, self)`.
- `super(B, self)` means "start after `B` in `type(self).__mro__`" — the explicit form is also what you need inside a `classmethod` (`super(B, cls)`).

!!! warning "Hard-coding the parent breaks multiple inheritance"
    `A.go(self)` instead of `super().go()` works until someone puts your class in a diamond — then it skips every sibling between you and `A`. Always route through `super()`, even when you are sure there is only one base.

## MRO and C3 linearisation

The MRO is computed once, at class creation, by the C3 linearisation algorithm. It guarantees that every class precedes its own bases, and that bases keep the left-to-right order they were listed in.

- Read it with `cls.__mro__` or `cls.mro()`.
- An ordering that cannot satisfy both rules is rejected at `class` time:

```python
class A: pass
class B(A): pass
class C(A): pass
class D(B, C): pass
class E(C, B): pass
class F(D, E): pass   # TypeError: Cannot create a consistent method
                      # resolution order (MRO) for bases B, C
```

`D` requires `B` before `C`, `E` requires the reverse; `F` would need both.

## Cooperative multiple inheritance

A diamond only works if *every* class in the chain calls `super()` and tolerates arguments it does not recognise. The usual contract: accept `**kwargs` and pass the remainder up.

```python
class Loggable:
    def __init__(self, *, log_level: str = "INFO", **kwargs) -> None:
        super().__init__(**kwargs)     # never a dead end — object.__init__ ends it
        self.log_level = log_level

class Timestamped:
    def __init__(self, *, tz: str = "UTC", **kwargs) -> None:
        super().__init__(**kwargs)
        self.tz = tz

class Event(Loggable, Timestamped):
    pass

e = Event(log_level="DEBUG", tz="Europe/Rome")
```

- Keyword-only parameters make the chain order-independent; positional arguments through a diamond are fragile.
- One class that forgets `super().__init__()` truncates the chain, and the classes after it in the MRO never initialise.

## Mixins

A mixin is a small class that supplies behaviour but is never instantiated on its own and holds no state of its own beyond what the host provides.

```python
class AsDictMixin:
    def as_dict(self) -> dict:
        return dict(vars(self))

class Reported(AsDictMixin, Account):   # mixins to the left of the real base
    pass

Reported(100.0).as_dict()               # {'balance': 100.0}
```

- Listed **left** of the substantive base so their methods win in the MRO.
- Name them `...Mixin` and keep them dependency-light: a mixin that assumes `self.balance` exists is coupled to its hosts whether or not it says so.
- To attach a mixin to a base chosen at runtime, build the class with a [class factory](class-factories.md#injecting-a-mixin) instead of a `class` statement.

## Subclassing built-in types

`dict`, `list`, and `str` are implemented in C and call their own internals directly, not your overrides. So an override applies to the operations you invoke explicitly and is skipped by the rest.

```python
class Upper(dict):
    def __setitem__(self, key, value):
        super().__setitem__(key.upper(), value)

d = Upper(a=1)      # {'a': 1}   — __init__ bypassed __setitem__
d["b"] = 2          # {'a': 1, 'B': 2}  — explicit call, honoured
d.update(c=3)       # {'a': 1, 'B': 2, 'c': 3}  — update bypassed it too
```

The fix is `collections.UserDict` (also `UserList`, `UserString`), which holds a real `dict` in `self.data` and routes every operation through the dunder methods:

```python
from collections import UserDict

class Upper(UserDict):
    def __setitem__(self, key, value):
        self.data[key.upper()] = value

Upper(a=1)          # {'A': 1}  — consistent everywhere
```

- Methods returning new objects also drop the subclass: `list` slicing gives a plain `list`, and `int`/`str` arithmetic and concatenation return the base type.
- Subclassing `dict`/`list` purely for a fixed, small set of behaviours is fine; subclassing them to *redefine* their semantics is not.

## Overrides and typing

Static type checkers enforce the Liskov Substitution Principle (LSP): a `Child` must be usable everywhere a `Parent` is. For an override, that means parameter types may only widen and the return type may only narrow.

```python
class Base:
    def feed(self, x: int) -> object: ...

class Ok(Base):
    def feed(self, x: int | str) -> str: ...   # wider param, narrower return — fine

class Bad(Base):
    def feed(self, x: str) -> object: ...      # mypy: incompatible with supertype "Base"
```

- Narrowing a parameter, dropping one, or raising a *new* exception type the caller cannot expect are all LSP violations, even when Python itself runs them happily.
- Use `typing.override` (Python 3.12+) to assert that a method really does override something — a renamed parent method then becomes a type error instead of a dead subclass method:

```python
from typing import override

class Savings(Account):
    @override
    def describe(self) -> str: ...
```

!!! tip "Prefer composition, and an abstract base when you do subclass"
    Inheritance couples you to the parent's *implementation*, so a parent refactor can break children that never changed. Subclass when the child genuinely *is* a parent and the parent was designed for it — an abstract base class (ABC) with `@abstractmethod`, per [oop.md](oop.md) — and otherwise hold the other object as an attribute. For an interface with no inheritance at all, use `Protocol` ([structural-typing.md](../../typing/structural-typing.md)).

## Inspecting the relationship

```python
issubclass(Savings, Account)    # True — class-level
isinstance(Savings(0, 0.1), Account)   # True — instance-level
Account.__subclasses__()        # [Savings] — direct children only, live
Savings.__bases__               # (Account,) — as written in the class statement
```

- `__subclasses__()` sees only classes that have actually been imported.
- `register()` on an `abc.ABCMeta` class creates a **virtual** subclass: `issubclass` answers `True`, but nothing is inherited and abstract methods are not enforced.
- To run code whenever a subclass is defined — registration, validation of required attributes — use `__init_subclass__`, covered in [class-creation.md](class-creation.md).

See also: [oop.md](oop.md) for ABCs and the composition-over-inheritance argument; [data-model.md](data-model.md) for `__new__` vs `__init__` in a subclass; [exceptions.md](../exceptions.md) for subclassing `Exception`.
