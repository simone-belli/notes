---
tags:
  - design-patterns
---

# Class factories

A function that takes a class and returns a new class derived from it. Classes are ordinary runtime objects, so nothing special is needed — a [`class` statement is sugar](class-creation.md#classes-vs-metaclasses-the-instance-of-chain-one-level-up) for calling a metaclass, and a factory makes that call itself.

```python
Loud = make_loud(Base)
issubclass(Loud, Base)   # True
```

This *derives* a second class; the original is untouched. Rewriting `Base.greet` instead is monkey-patching, and affects everyone who already imported `Base`.

## A `class` statement inside the function

The readable default — the base is just a name in scope:

```python
class Base:
    def greet(self): return "hi"

def make_loud(base):
    class Loud(base):
        def greet(self):
            return super().greet().upper()
    Loud.__name__ = Loud.__qualname__ = f"Loud{base.__name__}"
    return Loud

make_loud(Base)().greet()   # 'HI'
```

- Zero-argument `super()` works: a real class body gets the compiler's `__class__` cell.
- Decorators, annotations, `__slots__` and docstrings all behave normally.
- Fix `__name__`/`__qualname__` by hand — every call otherwise produces a class literally named `Loud`.

## `type(name, bases, namespace)`

The three-argument form of `type` is the class constructor. Use it when the name, bases, or method set is computed:

```python
def make_loud(cls):
    def greet(self):
        return cls.greet(self).upper()      # explicit base call, not super()
    name = f"Loud{cls.__name__}"
    return type(name, (cls,), {"greet": greet, "__qualname__": name})
```

- `name` → `__name__`; `bases` → the tuple the Method Resolution Order (MRO) is built from; `namespace` → the class `__dict__`.
- Keyword arguments after the dict go to `__init_subclass__`, exactly as in a `class C(Base, label="x")` statement: `type("C", (Plugin,), {}, label="y")`.
- Descriptors in the namespace still receive [`__set_name__`](attribute-lookup.md#the-descriptor-protocol) — the metaclass calls it for every value.

!!! warning "No zero-argument `super()` in an injected function"
    `super()` needs a `__class__` cell that only exists for functions defined inside a class body. A plain `def` stuffed into a namespace dict raises `RuntimeError: super(): __class__ cell not found`. Call the base explicitly (`cls.greet(self)`), or use a `class` statement.

## `types.new_class` — the correct general tool

`type(...)` *is* the default metaclass, so calling it bypasses metaclass resolution, `__prepare__`, and `__mro_entries__` (PEP 560). `types.new_class(name, bases=(), kwds=None, exec_body=None)` runs the full protocol:

```python
import types

def make_loud(base):
    def body(ns):
        ns["greet"] = lambda self: "LOUD"
        ns["__module__"] = __name__
    return types.new_class(f"Loud{base.__name__}", (base,), exec_body=body)
```

Required, not merely tidier, when the base is a [generic alias](../../typing/subscriptable.md) or an `Enum`:

```python
import types
from typing import Generic, TypeVar

T = TypeVar("T")
class G(Generic[T]): ...

type("Bad", (G[int],), {})          # TypeError: type() doesn't support MRO entry
                                    #   resolution; use types.new_class()
types.new_class("Good", (G[int],), {})       # works; __orig_bases__ == (G[int],)
```

`types.prepare_class(name, bases, kwds)` exposes just the first half, returning `(metaclass, namespace, kwds)`.

!!! warning "`types.new_class` sets `__module__` to `types`"
    `__module__` comes from the globals of the frame that calls the metaclass — `types.py` itself. Set `ns["__module__"] = __name__` in `exec_body`, or the class claims to live in the standard library and breaks `repr`, `pickle`, and doc tools. Plain `type(...)` gets this right, since you are the caller.

## Injecting a mixin

The common real use: add behaviour, keep the original. The [mixin](subclassing.md#mixins) goes first so it wins in the MRO.

```python
class LoggingMixin:
    def save(self, *a, **k):
        print(f"saving {self!r}")
        return super().save(*a, **k)

def with_logging(cls):
    name = f"Logged{cls.__name__}"
    return type(name, (LoggingMixin, cls), {"__qualname__": name})
```

MRO is `(LoggedX, LoggingMixin, X, object)`, so `super().save` in the mixin finds `X.save` — [cooperative multiple inheritance](subclassing.md#cooperative-multiple-inheritance) driven purely by base order.

## Identity and caching

Every call builds a fresh class; two identically built classes are different objects.

```python
import functools

make_loud(Base) is make_loud(Base)                 # False
isinstance(make_loud(Base)(), make_loud(Base))     # False

@functools.cache                                   # one class per base
def make_loud(base): ...
```

[`functools.cache`](../../functional/functools.md) keys on the base class and keeps it alive forever — fine for a fixed set of inputs, a leak if the inputs are themselves generated. Use `lru_cache(maxsize=...)` or a `weakref.WeakKeyDictionary` then.

## Pickling

`pickle` stores a class by reference (module + qualified name) and re-imports it, so a class no module-level name points to cannot be found:

```python
import pickle
pickle.dumps(make_loud(Base)())
# PicklingError: Can't pickle <class '__main__.LoudBase'>:
#   attribute lookup LoudBase on __main__ failed
```

- Best: don't pickle instances of generated classes (this includes `multiprocessing` arguments).
- Otherwise bind the class into module globals under its own name, with `__module__` and `__qualname__` set to match:

    ```python
    globals()[name] = new
    ```

## Typing

```python
from typing import TypeVar

T = TypeVar("T")

def with_logging(cls: type[T]) -> type[T]: ...
```

`type[T] -> type[T]` is the honest signature: the result is usable wherever a `T` was. No static checker can see the members the factory *adds* — they exist only at runtime. If callers need them, declare the mixin as a [`Protocol`](../../typing/structural-typing.md) and annotate against that, or write the subclass out by hand.

## Pitfalls

- **Some types are final** — `bool`, `NoneType`, `range`, `slice` reject subclassing at the C level (see [the built-in-type trap](subclassing.md#subclassing-built-in-types)); an `Enum` *with members* is closed too (`TypeError: <enum 'More'> cannot extend <enum 'Color'>`).
- **`__slots__` must be in the namespace you pass** — assigning it afterwards does nothing, the descriptors are built at construction time.
- **Metaclass conflicts** surface as `TypeError: metaclass conflict`; `types.new_class` reports them the same way a `class` statement does.
- **A class decorator that returns a subclass** leaves two classes with the same name in the MRO, which confuses tracebacks and `pickle`. Prefer an explicit `Loud = make_loud(Greeter)` call so the reader sees both.
- **A generated subclass of a [dataclass](../dataclasses.md) isn't one** until the decorator is re-applied, and new fields need `__annotations__` in the namespace:

    ```python
    import dataclasses

    Sub = dataclasses.dataclass(
        type("Point3", (Point,), {"__annotations__": {"z": int}, "z": 0})
    )
    ```

## When not to

- **Registering or validating subclasses** → [`__init_subclass__`](class-creation.md#__init_subclass__-lightweight-hook-after-a-subclass-exists), and let the subclasses be written normally.
- **Wrapping behaviour of an object** → wrap the instance, not the class ([composition over inheritance](oop.md)).
- **A handful of known variants** → write them out as classes.
- **Changing what *other* people's `class` statements do** → that is a [metaclass](class-creation.md#metaclasses-full-control-before-the-class-exists); a factory is only you calling the constructor.
