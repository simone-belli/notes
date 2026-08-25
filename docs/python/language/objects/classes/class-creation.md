---
tags:
  - design-patterns
---

# Class body execution and class creation

A `class` statement is executable code, run once, top to bottom, at definition time — not a declarative schema. Whatever names get bound during that run become the class's namespace, which is then handed to a metaclass to assemble into the class object.

```python
class C:
    print("runs once, at import time")
    x = 1
    def method(self): ...
```

Nothing about `C()` appears here — the body runs exactly once regardless of how many (or how few) instances are ever created.

## Classes vs. metaclasses: the instance-of chain, one level up

A class is itself an object, so it has a type — that type is its **metaclass**. This is the same *instance-of* relationship as `isinstance(obj, C)`, just one level higher:

```python
type(5)      # <class 'int'>   — 5 is an instance of int
type(int)    # <class 'type'>  — int is an instance of type (the default metaclass)
type(type)   # <class 'type'>  — type is an instance of itself: the base case that stops the chain
```

`type` is unusual in being both the function that inspects an object's class (`type(obj)`) *and* the mechanism that constructs classes — a `class` statement is sugar for calling a metaclass with `(name, bases, namespace)`:

```python
class Point:
    def __init__(self, x, y): self.x, self.y = x, y

# equivalent to:
Point = type("Point", (), {"__init__": lambda self, x, y: setattr(self, "x", x) or setattr(self, "y", y)})
```

A custom metaclass must itself derive from `type` — since `isinstance` is transitive through inheritance, every class remains an instance of `type` no matter its metaclass:

```python
class Meta(type): pass
class C(metaclass=Meta): pass

isinstance(C, Meta)   # True
isinstance(C, type)   # True — Meta is-a type, so C is transitively an instance of type too
```

!!! note "Different questions, same hierarchy"
    A method on `C` is available to `C()` instances. A method on `C`'s metaclass is available on `C` itself (`C.some_meta_method()`), not on its instances — conflating the two is the most common source of metaclass confusion.

## Why decorators inside a class body fire at definition time

A `@decorator` on a method inside the body runs the instant that `def` executes — i.e. during class-body execution, before the class object even exists. This is how a [registering decorator](../../functional/decorators.md#transforming-vs-registering) accumulates entries in one place:

```python
registry = {}

def register(func):
    registry[func.__name__] = func   # side effect, fires immediately
    return func

class Handlers:
    @register
    def on_start(self): ...

# registry is already populated here — before Handlers() is ever called
```

The registering decorator itself can't see the finished class (it doesn't exist yet); it can only write to something outside it, or mark the function for something else to find later.

## `__init_subclass__` — lightweight hook after a subclass exists

Runs automatically once a subclass's body has finished and the subclass object exists — no metaclass needed:

```python
class Plugin:
    _registry = []
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        Plugin._registry.append(cls)

class CSVPlugin(Plugin): ...
class JSONPlugin(Plugin): ...

Plugin._registry   # [CSVPlugin, JSONPlugin]
```

## Metaclasses — full control before the class exists

A metaclass (`type` by default) receives the raw `(name, bases, namespace)` triple and constructs the class object itself, so it can rewrite the namespace before the class exists at all — `type.__new__` here is the same [`__new__` protocol](data-model.md#new-vs-init) used to construct ordinary instances, just one level up: metaclass is to class as class is to instance.

```python
class Meta(type):
    def __new__(mcs, name, bases, namespace, **kwargs):
        print(f"building {name}: {list(namespace)}")
        return super().__new__(mcs, name, bases, namespace, **kwargs)

class C(metaclass=Meta): ...
```

!!! note "`__init_subclass__` vs metaclass"
    `__init_subclass__` only runs *after* a valid class already exists — simpler, but can't reject or rewrite the class itself. A metaclass intercepts construction *before* the class exists, so it can alter or refuse it — strictly more powerful, harder to compose (a class has exactly one metaclass, and all bases' metaclasses must be compatible). Default to `__init_subclass__` for registries/plugin patterns.

`__set_name__` (see [attribute-lookup.md](attribute-lookup.md#the-descriptor-protocol)) is called by this same construction step, after the namespace exists — which is why it can be told the attribute's name, something a decorator running earlier during body execution has no way to know.

See [oop.md](oop.md) for the Method Resolution Order (MRO) these constructed classes participate in.
