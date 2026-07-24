---
tags:
  - design-patterns
---

# Attribute lookup protocol

`obj.x` is not a dict lookup — it's an algorithm (`object.__getattribute__`) that walks a fixed order of places. Every "magic" attribute feature (`@property`, bound methods, `__slots__`, `__getattr__`) is a special case of intercepting one step of this walk.

## The lookup order

1. Search `type(obj).__mro__` for `x`. If found and it's a **data descriptor** (defines `__get__` *and* `__set__`) — call its `__get__` and return. Stop.
2. Otherwise check `obj.__dict__`. If `x` is there, return it. Stop.
3. Otherwise, if step 1 found a **non-data descriptor** (only `__get__`, e.g. a function) — call its `__get__`; if it found a plain value — return it as-is.
4. Otherwise, fall back to `__getattr__(obj, 'x')` if defined, else raise `AttributeError`.

!!! note "Why data descriptors beat the instance dict, but non-data descriptors don't"
    If a plain instance attribute could shadow a `property`, `self.x = 5` would silently bypass a validating setter. Data descriptors sit above instance state so they always intercept both read and write. Functions (non-data descriptors) have no `__set__` to protect, so `self.method = ...` can shadow a bound method per-instance.

## Descriptors

A **descriptor** is any object whose class defines `__get__`/`__set__`/`__delete__`. `property`, `classmethod`, `staticmethod`, and functions themselves are all ordinary descriptors — not interpreter-special-cased — found via the MRO walk in step 1/3.

```python
class Descriptor:
    def __get__(self, obj, objtype=None):
        return 42
    def __set__(self, obj, value):
        print(f"validating {value}")

class C:
    x = Descriptor()
```

Functions are the canonical non-data descriptor: `f.__get__(instance, cls)` produces a bound method, which is why `instance.method()` implicitly passes `self`. `staticmethod`/`classmethod` are thin wrappers customizing that `__get__` to skip or redirect the binding.

## `__getattr__` vs `__getattribute__`

| | Called | Use for |
|---|---|---|
| `__getattr__` | Only as fallback, after the whole protocol above finds nothing | Lazy attributes, proxies, dynamic APIs |
| `__getattribute__` | Unconditionally, on *every* attribute access — it **is** the algorithm | Full interception (rare) |

!!! warning "`__getattribute__` is a scalpel"
    Overriding it and then accessing `self.x` inside the override re-invokes it — an easy infinite recursion. Reach for `__getattr__` instead unless you must intercept accesses that would otherwise succeed.

## `__slots__`

`__slots__ = ('x',)` generates a data descriptor per name and removes the instance `__dict__` entirely — step 2 above no longer exists, which is both why slotted objects save memory and why they reject new dynamic attributes.

## Setting attributes (mirror algorithm)

`obj.x = value` → `object.__setattr__`: check the MRO for a data descriptor and call its `__set__`; otherwise write directly into `obj.__dict__`. Non-data descriptors never intercept writes — only data descriptors (like `property`) can enforce invariants on assignment.

See [oop.md](oop.md) for the Method Resolution Order (MRO) itself and [data-model.md](data-model.md) for dunder methods more broadly.
