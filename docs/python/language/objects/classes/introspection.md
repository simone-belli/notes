# Class introspection

Two different questions hide behind "does this class have `x`?":

- **Does the member exist?** A runtime question about the object — `hasattr`, `getattr`, `inspect`.
- **Does the class's code *call* `x`?** A static question about source text — the `ast` module. No runtime check can answer it: a method body touches nothing until it runs.

## `hasattr` / `getattr`

```python
class Duck:
    sound = "quack"
    def quack(self) -> str:
        return self.sound

hasattr(Duck, "quack")                    # True
getattr(Duck, "fly", None)                # None — no exception
callable(getattr(Duck, "quack", None))    # True — a method, not data
```

- `hasattr(obj, "x")` is defined as "`getattr` it; `False` if that raises `AttributeError`, else `True`".
- That means it **runs code**: if `x` is a `property`, the getter executes. Other exception types propagate out of `hasattr`.
- `callable(getattr(obj, "x", None))` is the practical "can I call `obj.x()`" test.

!!! warning "`hasattr` lies about properties that raise `AttributeError`"
    ```python
    class Lazy:
        @property
        def config(self):
            raise AttributeError("not loaded yet")

    hasattr(Lazy(), "config")   # False — but `config` *is* defined
    ```
    Anything with `__getattr__` fails the other way: a proxy fabricating attributes makes `hasattr` always `True`.

## Class vs instance

A class and its instances have different attribute sets — the most common source of a wrong answer.

```python
class Trade:
    symbol: str                 # annotation only — NOT an attribute
    venue = "LSE"               # class attribute
    def __init__(self, qty: int) -> None:
        self.qty = qty          # instance attribute, exists after __init__

hasattr(Trade, "venue")     # True
hasattr(Trade, "qty")       # False — lives on instances
hasattr(Trade, "symbol")    # False — a bare annotation creates no attribute
hasattr(Trade(10), "qty")   # True
```

A bare `symbol: str` lands in `Trade.__annotations__` and never in `Trade.__dict__`, so "does the class *declare* `symbol`?" is an annotations question:

```python
import inspect

inspect.get_annotations(Trade)     # {'symbol': <class 'str'>}  (3.10+)
```

Prefer `inspect.get_annotations` over reading `__annotations__`: before 3.10 a class with no annotations of its own inherits the parent's dict, silently reporting a parent's declarations as the child's. See [class-attributes.md](class-attributes.md) for the class/instance split itself.

## Defined here vs inherited

`hasattr` walks the whole Method Resolution Order (MRO). The class's own `__dict__` answers "did *this* class define it?".

```python
class Base:
    def run(self): ...
    def stop(self): ...

class Child(Base):
    def run(self): ...          # overridden

"run"  in Child.__dict__        # True  — defined here
"stop" in Child.__dict__        # False — inherited
"stop" in dir(Child)            # True  — reachable

Child.stop is Base.stop         # True → not overridden

# Which class in the MRO supplies it?
next(k for k in Child.__mro__ if "stop" in k.__dict__)   # <class 'Base'>
```

`vars(Child)` is the same mapping as `Child.__dict__` (a read-only `mappingproxy`). The `is` comparison works because accessing a function through a class yields the plain function object.

## `inspect.getattr_static` — asking without executing

```python
import inspect

class Proxy:
    def __getattr__(self, name):             # fabricates anything asked of it
        return lambda: f"dynamic {name}"

hasattr(Proxy(), "anything")                       # True — __getattr__ answered
inspect.getattr_static(Proxy(), "anything", None)  # None — nothing is really there
```

`getattr_static` skips `__getattribute__`, `__getattr__`, and the [descriptor protocol](attribute-lookup.md), returning the raw object found on the class — the function, or the `property` object itself rather than its value. Use it on expensive or dynamic objects (ORM models, mocks, lazy proxies); accept that it cannot see attributes that only exist dynamically.

## Classifying and matching a member

```python
import inspect

inspect.isfunction(Duck.__dict__["quack"])     # True  — plain function
inspect.ismethod(Duck.quack)                   # False — unbound: just a function
inspect.ismethod(Duck().quack)                 # True  — bound method
inspect.isroutine(Duck.quack)                  # function OR builtin/C method
inspect.isdatadescriptor(x)                    # property, slot, __set__ descriptor
inspect.getmembers(Duck, inspect.isfunction)   # [('quack', <function ...>)]

list(inspect.signature(Duck.quack).parameters)         # ['self']
inspect.signature(Duck.quack).bind(Duck(), 1)          # TypeError: too many positional arguments
```

`getmembers(cls, predicate)` enumerates; `signature(...).bind(...)` tests whether a specific call would be accepted.

## Better than asking

!!! tip "An explicit `hasattr` is usually a design smell"
    Three alternatives, in increasing order of strictness.

**EAFP — just do it.** No time-of-check/time-of-use gap (see [exceptions.md](../exceptions.md)):

```python
try:
    obj.flush()
except AttributeError:
    pass
```

**Declare the shape with `Protocol`.** Static checkers verify signatures; `isinstance` verifies names only.

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Quackable(Protocol):
    def quack(self) -> str: ...

isinstance(Duck(), Quackable)    # True — a quack(self, loudly) also passes
```

See [structural-typing.md](../../typing/structural-typing.md) for the signature-fidelity checks `isinstance` can't do.

**Enforce at class-creation time.** `abstractmethod` defers the error to instantiation; `__init_subclass__` raises at `class` statement time.

```python
from abc import ABC, abstractmethod

class Job(ABC):
    @abstractmethod
    def run(self) -> None: ...

class Broken(Job): ...
Broken.__abstractmethods__   # frozenset({'run'}) — what's still missing
Broken()                     # TypeError: Can't instantiate abstract class Broken ...
```

```python
class Job:
    def __init_subclass__(cls, **kw):
        super().__init_subclass__(**kw)
        if not callable(getattr(cls, "run", None)):
            raise TypeError(f"{cls.__name__} must define run()")
```

See [oop.md](oop.md) for Abstract Base Classes (ABCs) and [class-creation.md](class-creation.md) for `__init_subclass__`.

## Does the class *call* it?

The `ast` module parses source without executing it. Find the `ClassDef`, then walk it for `ast.Call` nodes:

```python
import ast

tree = ast.parse(open("trades.py", encoding="utf-8").read())

def called_names(node: ast.AST) -> set[str]:
    """Every name syntactically called inside `node`."""
    names = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            fn = child.func
            if isinstance(fn, ast.Name):            # log_event(...)
                names.add(fn.id)
            elif isinstance(fn, ast.Attribute):     # self.log(...) / mod.log(...)
                names.add(fn.attr)
    return names

for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
    print(cls.name, sorted(called_names(cls)))      # Trade ['log_event', 'notify']
```

- The two `ast.Call.func` shapes: `ast.Name` (bare call, use `.id`) and `ast.Attribute` (anything dotted — `.attr` is the final name, `.value` the object).
- For attribute *access* rather than calls, collect bare `ast.Attribute` nodes; for attributes being set, inspect `ast.Assign` / `ast.AnnAssign` targets.
- `ast.unparse(node)` (3.9+) turns a node back into source — handy for debugging such a script.

With an object but no source, `__code__.co_names` lists the global and attribute names the bytecode references:

```python
Trade.settle.__code__.co_names      # ('log_event', 'notify')
```

It is coarse — it mixes plain attribute reads with calls (`return self.sound` gives `('sound',)`) and carries no structure. `dis` has the detail, but opcode names shift between releases (CPython 3.12 removed `LOAD_METHOD`, folding it into `LOAD_ATTR` with a flag bit), so prefer the Abstract Syntax Tree (AST).

!!! note "Static analysis can only approximate"
    `getattr(obj, name)()` puts the name nowhere in the source; decorators insert and hide calls; `self.run()` doesn't say *which* class's `run` runs; and a call in the source may be dead code. For "did it actually call it?", patch the target and assert on the record (see [mocking.md](../../../testing/mocking.md)):

    ```python
    from unittest.mock import patch

    with patch("trades.log_event") as spy:
        Trade(10).settle()
        spy.assert_called_once()
    ```

## Decision table

| Question | Tool |
|---|---|
| Can I call `obj.x()` right now? | `callable(getattr(obj, "x", None))` |
| Is the name defined, without running code? | `inspect.getattr_static(obj, "x", None)` |
| Did *this* class define it, not a parent? | `"x" in cls.__dict__` |
| Which class supplies it? | walk `cls.__mro__` |
| Is an attribute declared but unassigned? | `inspect.get_annotations(cls)` |
| Does it match a required shape? | `Protocol` + mypy; `@runtime_checkable` for names |
| Must every subclass implement it? | `abstractmethod` / `__init_subclass__` |
| Does the source *call* a function? | `ast.parse` + `ast.walk` for `ast.Call` |
| Did it call it in this run? | `unittest.mock.patch` + `assert_called` |
