# Slicing

The colon syntax does no slicing. `obj[1:5:2]` builds a `slice` object and passes it to
[`__getitem__`](../../typing/subscriptable.md) — every container decides for itself what to do
with it:

```python
obj[1:5:2]   # → type(obj).__getitem__(obj, slice(1, 5, 2))
```

`slice` is a builtin (no import) taking 1–3 arguments with `range`'s defaults: `slice(5)` is
`slice(None, 5, None)`.

## What arrives as `key`

| Written | `key` received |
|---|---|
| `obj[3]` | `3` |
| `obj[1:5:2]` | `slice(1, 5, 2)` |
| `obj[:]` | `slice(None, None, None)` |
| `obj[::-1]` | `slice(None, None, -1)` |
| `obj['a':'b']` | `slice('a', 'b', None)` |
| `obj[1, 2]` | `(1, 2)` — a tuple |
| `obj[:, 0]` | `(slice(None, None, None), 0)` |
| `obj[...]` | `Ellipsis` |

- Omitted components are `None`, never `0` or `len` — you decide what `None` means.
- Components are unvalidated and need not be integers. `slice('a', 'b')` is legal, which is how
  [pandas](../../../../data/pandas/indexing.md) supports `df.loc['2024-01':'2024-06']`.
- A comma makes the key a **tuple**; `...` is the singleton `Ellipsis`. NumPy's multi-axis
  indexing is just unpacking that tuple — no special syntax involved.

!!! tip "`slice.indices(length)` does the arithmetic"
    `.start` / `.stop` / `.step` are raw: possibly `None`, negative, or past the end.
    `key.indices(len(self))` returns a normalised `(start, stop, step)` clamped to that length,
    so `range(*key.indices(len(self)))` yields the exact positions to visit. Essential when the
    container isn't backed by something already sliceable — a generator, a file, a query.

```python
s = slice(None, 10, 2)
s.indices(5)                  # (0, 5, 2) — clamped
list(range(*s.indices(5)))    # [0, 2, 4]
```

## A generic `__getitem__`

```python
import operator
from collections.abc import Sequence
from typing import Self, overload


class TimeSeries(Sequence[float]):
    def __init__(self, values: Sequence[float]) -> None:
        self._values = list(values)

    def __len__(self) -> int:
        return len(self._values)

    @overload
    def __getitem__(self, key: int) -> float: ...
    @overload
    def __getitem__(self, key: slice) -> Self: ...

    def __getitem__(self, key: int | slice) -> float | Self:
        if isinstance(key, slice):
            return type(self)(self._values[key])    # same class back
        return self._values[operator.index(key)]    # IndexError if out of range
```

- **A slice returns your own type; an index returns an element.** `list[1:3]` is a `list`,
  `str[1:3]` is a `str` — returning the bare backing list breaks `ts[10:20][::2]`. Use
  `type(self)(...)`, not the class name, so subclasses slice into themselves.
- **Use `operator.index(key)`, not `isinstance(key, int)`.** It calls `__index__`, accepting
  `bool` and `numpy.int64` while rejecting `float` with the same `TypeError` the built-ins give.
- **Ignoring `.step` is a silent bug.** If you can't honour it, raise on
  `key.step not in (None, 1)`.
- Two [`@overload`](../../typing/typing.md) stubs let a type checker know that `ts[0]` is a
  `float` but `ts[0:2]` is a `TimeSeries`.

!!! warning "Out of range must raise `IndexError`"
    A class with `__getitem__` but no `__iter__` falls back to the legacy iteration protocol:
    Python calls `obj[0]`, `obj[1]`, … and only an `IndexError` stops the loop. Return `None` or
    raise `ValueError` instead and `for x in obj` never terminates or fails with the wrong
    exception. Delegating to a real list gets this right for free.

## `Sequence` supplies the rest

Given `__len__` and `__getitem__`, the `collections.abc.Sequence` Abstract Base Class (ABC)
mixes in `__contains__`, `__iter__`, `__reversed__`, `index`, and `count`
(see [ABCs](oop.md)):

```python
ts = TimeSeries([1.0, 2.0, 3.0])
2.0 in ts               # True
list(reversed(ts))      # [3.0, 2.0, 1.0]
ts.index(3.0)           # 2
```

The mixins never touch `__getitem__`'s return value, so inheriting does **not** make slices
return your type — that stays your job.

## Writing through a slice

`__setitem__` and `__delitem__` receive the same key objects, so the same
`isinstance(key, slice)` dispatch applies. One built-in rule to mirror: an *extended* slice
(step other than 1) requires matching lengths, while a contiguous slice may resize.

```python
xs = [0, 1, 2, 3, 4]
xs[1:3] = [9]      # [0, 9, 3, 4] — contiguous slice may resize
xs[::2] = [9, 9]   # ValueError: attempt to assign sequence of size 2
                   #             to extended slice of size 3
```

!!! note "Hashable only from Python 3.12"
    `slice` objects were deliberately unhashable before 3.12, so they couldn't be `dict` keys or
    memoised with `functools.lru_cache`. To cache slice lookups on 3.11 and earlier, key on
    `(key.start, key.stop, key.step)`.

## Related

- [Subscriptable Types](../../typing/subscriptable.md) — `__getitem__` vs `__class_getitem__`
  and generic aliases
- [The Data Model and Pythonic Objects](data-model.md) — the wider dunder protocol
- [Iterators and Generators](../../functional/iterators-generators.md) — the `__iter__` protocol
  that supersedes the `__getitem__` fallback
