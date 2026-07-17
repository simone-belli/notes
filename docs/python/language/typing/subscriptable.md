---
tags:
  - typing
quiz: detail
---

# Subscriptable Types

`obj[key]` is syntactic sugar for `type(obj).__getitem__(obj, key)`. A type that doesn't define `__getitem__` raises:

```
TypeError: 'X' object is not subscriptable
```

## Instance subscripting — `__getitem__`

Built-ins with `__getitem__`: `list`, `tuple`, `str`, `bytes`, `dict`, `numpy.ndarray`, `pandas.Series`.  
Built-ins without: `int`, `float`, `bool`, `NoneType`, `set` (iterable but unordered — no indexing).

```python
42[0]      # TypeError: 'int' object is not subscriptable
{1, 2}[0]  # TypeError: 'set' object is not subscriptable
```

Implement it in your own class to support `[]`:

```python
class TimeSeries:
    def __init__(self, data): self._data = data
    def __getitem__(self, key): return self._data[key]  # slices arrive as slice objects
```

## Type / class subscripting — `__class_getitem__`

There's a second kind of subscripting: applying `[]` to a *class object*, used for generic type annotations:

```python
list[int]        # subscripts the class list, not an instance
dict[str, float]
```

This calls `list.__class_getitem__(int)`, which returns a `types.GenericAlias` — metadata for type checkers; no runtime enforcement.

**`__class_getitem__` was added to built-in types in Python 3.9 (PEP 585).** On 3.8 and earlier, `list[int]` raises `TypeError: 'type' object is not subscriptable`.

### Pre-3.9 fixes

**Option 1 — use `typing` wrappers** (capital-letter aliases that have `__class_getitem__`):

```python
from typing import List, Dict, Tuple, Optional

def process(items: List[int]) -> Dict[str, int]: ...
```

**Option 2 — defer annotation evaluation** (annotations stored as strings, never executed at import):

```python
from __future__ import annotations   # top of file; works on 3.7+

def process(items: list[int]) -> dict[str, int]: ...  # no runtime error
```

### What `list[int]` returns

```python
list[int].__origin__  # <class 'list'>
list[int].__args__    # (<class 'int'>,)
```

A `GenericAlias` — pure metadata. A `list[int]` variable can still hold any type at runtime; Python doesn't enforce it.

## Generic classes

To make your own class subscriptable as a type hint, inherit from `Generic`:

```python
from typing import Generic, TypeVar

T = TypeVar("T")

class Stack(Generic[T]):
    def push(self, item: T) -> None: ...
    def pop(self) -> T: ...

# Stack[int] now returns a proper generic alias
```

## Common errors at a glance

!!! tip "'NoneType' object is not subscriptable — the variable you're indexing is None"
    This is the most frequent subscript error in practice. Common causes: a function that forgets `return`, `dict.get()` returning `None` for a missing key, or an optional value that wasn't checked. Fix the source — add the missing `return`, use a default in `.get()`, or guard with `if x is not None`.

| Error | Cause | Fix |
|---|---|---|
| `'NoneType' object is not subscriptable` | variable is `None` (missed `return`, `.get()` returned `None`) | check for `None` first |
| `'set' object is not subscriptable` | sets are unordered | use `next(iter(s))` or convert to list |
| `'type' object is not subscriptable` | built-in generic on Python < 3.9 | `from __future__ import annotations` or use `typing.List` etc. |

`'NoneType'` is by far the most common in practice.

## Related

- [data-model.md](../objects/data-model.md) — dunder methods overview; `__getitem__` in context
- [../../tooling/mypy.md](../../tooling/mypy.md) — type checking generic aliases statically
