---
quiz: detail
---

# `itertools.groupby`

Groups consecutive elements of an iterable that share the same key. Like SQL `GROUP BY`, but **only groups adjacent elements** — input must be sorted by the key first.

## Basic usage

```python
from itertools import groupby

data = [1, 1, 2, 2, 2, 3, 1, 1]
for key, group in groupby(data):
    print(key, list(group))
# 1 [1, 1]
# 2 [2, 2, 2]
# 3 [3]
# 1 [1, 1]   ← new group; 1 appeared again non-consecutively
```

Each iteration yields `(key, group)` where `group` is a lazy iterator.

## Key function

```python
words = ["apple", "ant", "banana", "bee"]
words.sort(key=lambda w: w[0])  # sort first!

for letter, group in groupby(words, key=lambda w: w[0]):
    print(letter, list(group))
# a ['apple', 'ant']
# b ['banana', 'bee']
```

!!! warning "Two rules that must both hold: sort first, consume each group immediately"
    `groupby` only groups **adjacent** equal elements — unsorted input produces multiple groups for the same key. And the inner `group` iterator shares state with the outer loop: advancing past a key exhausts the previous group. Always sort by the key first, and always materialise each group with `list(g)` before the next iteration.

## Critical gotcha: consume each group before advancing

The `group` iterator shares state with the outer iterator. Advancing to the next key exhausts the current group.

```python
# WRONG — all groups are empty when accessed later
groups = {k: g for k, g in groupby([1, 1, 2, 2, 3])}

# RIGHT — materialise each group immediately
groups = {k: list(g) for k, g in groupby([1, 1, 2, 2, 3])}
# {1: [1, 1], 2: [2, 2], 3: [3]}
```

## Canonical sort → groupby pattern

```python
from operator import itemgetter

records = [
    {"name": "alice", "dept": "eng"},
    {"name": "bob",   "dept": "hr"},
    {"name": "carol", "dept": "eng"},
]

key = itemgetter("dept")  # or lambda r: r["dept"] — see ../operator.md
for dept, group in groupby(sorted(records, key=key), key=key):
    print(dept, [r["name"] for r in group])
# eng ['alice', 'carol']
# hr  ['bob']
```

## When to use `groupby` vs alternatives

| Situation | Use |
|-----------|-----|
| Already-sorted / streaming data | `groupby` |
| Unsorted data, need counts or aggregations | `collections.Counter` / `defaultdict` |
| DataFrames | `pandas.DataFrame.groupby` |

See also: [core.md](core.md) for `chain`, `islice`, `product`, and `combinations`; [../iterators-generators.md](../iterators-generators.md) for the iterator protocol.
