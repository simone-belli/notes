# Sets

An unordered collection of **unique, hashable** elements backed by a hash table. O(1) membership testing; no duplicates.

## Creation

```python
s = {1, 2, 3}                    # literal
s = set()                        # empty — {} alone is a dict
s = set([1, 2, 2, 3])            # from iterable: {1, 2, 3}
s = {x**2 for x in range(5)}    # set comprehension
```

Elements must be hashable (`int`, `str`, `tuple`, `frozenset` — not `list`, `dict`, `set`).

## Mutation

```python
s.add(4)        # no-op if already present
s.remove(4)     # KeyError if missing
s.discard(4)    # silent if missing
s.update([4,5]) # add multiple from any iterable
s.pop()         # remove and return arbitrary element
s.clear()
```

## Membership and iteration

```python
3 in s          # O(1)
len(s)
for x in s: ... # order is undefined — do not rely on it
```

## Set operations

Operators (`|`, `&`, `-`, `^`) require both operands to be sets. Methods (`.union()`, `.intersection()`, etc.) accept any iterable on the right.

```python
a = {1, 2, 3}
b = {2, 3, 4}

a | b   # union:                {1, 2, 3, 4}
a & b   # intersection:         {2, 3}
a - b   # difference (a not b): {1}
a ^ b   # symmetric difference: {1, 4}  — in one but not both

{1, 2} <= {1, 2, 3}          # subset (<=) / proper subset (<)
{1, 2, 3} >= {1, 2}          # superset
{1, 2}.isdisjoint({3, 4})    # True — no elements in common
```

In-place: `|=`, `&=`, `-=`, `^=`

## `frozenset` — immutable, hashable set

```python
fs = frozenset({1, 2, 3})    # no add/remove/clear
d = {frozenset({1, 2}): "x"} # can be a dict key or set element
```

All read operations work identically to `set`.

## Performance

| Operation       | Avg   |
|-----------------|-------|
| `x in s`        | O(1)  |
| `add`, `discard`| O(1)  |
| `s \| t`, `s & t` | O(len(s)+len(t)) |
| `s - t`         | O(len(s)) |

## Common patterns

```python
# Deduplication (loses order)
unique = list(set(items))

# Fast membership filtering — convert once, test many times in O(1)
excluded = set(excluded_list)
filtered = [x for x in items if x not in excluded]

# Set arithmetic
only_in_a = set_a - set_b
in_both   = set_a & set_b
```

## Gotchas

- `{}` is a `dict` — use `set()` for empty set
- `{1, 2} < {1, 2}` is `False` — `<` means *strict* subset
- `{1, 2} == {2, 1}` is `True` — sets are unordered

## Related

- [hash.md](hash.md) — why elements must be hashable; the `__eq__`/`__hash__` contract for custom classes
- [data-model.md](data-model.md) — `__contains__` dunder for custom membership testing
