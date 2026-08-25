---
quiz: core
---

# Unpacking Operators: `*x` and `**x`

`*` and `**` appear in expression and assignment contexts with different meanings. This note covers **expression context** (right-hand side) — what protocol `x` must satisfy.

## `*x` — iterable unpacking

Python calls `iter(x)` and consumes all items. `x` must implement:
- `__iter__` → returns an iterator, **or**
- `__getitem__` with integer keys starting at 0 (legacy sequence fallback)

### Contexts

**Function calls** — items become positional args:
```python
f(*[1, 2, 3])          # f(1, 2, 3)
f(*args, key=val)      # mix with keyword args
```

**Collection literals** — splice into another collection:
```python
[*a, *b]       # list  — concatenate
(*a, *b)       # tuple
{*a, *b}       # set (order not preserved)
[*a, 0, *b]    # interleave literals freely
```

Multiple `*` unpacks are allowed in a single call or literal (Python 3.5+).

### Custom class

```python
class MySeq:
    def __iter__(self):
        yield 1; yield 2; yield 3

print([*MySeq()])   # [1, 2, 3]
```

---

## `**x` — mapping unpacking

Python calls `x.keys()` then `x[key]` for each key. `x` must implement:
- `keys()` — returns an iterable of keys
- `__getitem__` — lookup by key

**`__iter__` is not required.** A class with only `keys()` and `__getitem__` works with `**` but not `*`.

### Contexts

**Function calls** — items become keyword args (keys must be strings):
```python
f(**{"a": 1, "b": 2})         # f(a=1, b=2)
f(**d, extra=3)                # mix with literal keyword
```

**Dict literals** — merge/overlay dicts:
```python
{**d1, **d2}           # merge; rightmost wins on conflict
{**d1, "key": 99}      # literal value overrides d1["key"]
```

Pre-3.9 idiom. From Python 3.9+, `d1 | d2` is cleaner for merging two dicts into a new one.

### Custom class

```python
class MyMapping:
    def keys(self):         return ["x", "y"]
    def __getitem__(self, k): return {"x": 10, "y": 20}[k]

print({**MyMapping()})  # {"x": 10, "y": 20}
```

---

## Starred assignment (LHS) — different syntax, same symbol

When `*` appears on the **left** of an assignment it captures a variable-length slice — no custom protocol needed:

```python
first, *rest = [1, 2, 3, 4]   # rest = [2, 3, 4]
*init, last  = [1, 2, 3, 4]   # init = [1, 2, 3]
a, *mid, z   = range(5)        # mid  = [1, 2, 3]
```

Only one `*` per assignment target.

---

## Mixing in function calls

```python
def f(a, b, c=0, d=0): ...
f(*[1, 2], **{"c": 3, "d": 4})   # f(1, 2, c=3, d=4)
```

---

!!! note "* and ** use different protocols — a class can support one but not the other"
    `*x` requires `__iter__` (iteration). `**x` requires `keys()` + `__getitem__` (mapping). A class with only `keys()` and `__getitem__` works with `**` in function calls but raises `TypeError` with `*`. This is why dicts support both, but a custom mapping that lacks `__iter__` only works with `**`.

## Protocol summary

| Operator | Requires | Does NOT require |
|----------|----------|-----------------|
| `*x` | `__iter__` (or `__getitem__(int)`) | `keys()` |
| `**x` | `keys()` + `__getitem__` | `__iter__` |

See [iterators-generators.md](iterators-generators.md) for the full iteration protocol and [data-model.md](../objects/classes/data-model.md) for dunder methods.
