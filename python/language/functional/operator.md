# `operator` — attrgetter, itemgetter, methodcaller

The `operator` module provides C-implemented callables for attribute, item, and method access. They replace common lambdas used as sort keys, `map` arguments, and `groupby` key functions.

Three reasons to prefer them over lambdas:
- **Faster** — no Python stack frame overhead (~20–40% on CPython for large sorts)
- **Declarative** — state what is accessed, not how
- **Picklable** — lambdas cannot be pickled; these can (required for `multiprocessing`)

---

## `itemgetter` — subscript access

```python
from operator import itemgetter

itemgetter(key)          # obj[key]
itemgetter(k1, k2, ...)  # (obj[k1], obj[k2], ...) — tuple
```

Works on tuples, lists, dicts, numpy arrays — anything subscriptable.

```python
rows = [('Alice', 30), ('Bob', 25)]
sorted(rows, key=itemgetter(1))                         # by age

sorted(data, key=itemgetter('dept', 'salary'))          # composite key
# vs lambda r: (r['dept'], r['salary'])
```

**Best use: same key for sort + groupby** — name it once, pass it twice:
```python
from operator import itemgetter
from itertools import groupby

by_desk = itemgetter('desk')
trades.sort(key=by_desk)
for desk, group in groupby(trades, key=by_desk):
    print(desk, sum(t['pnl'] for t in group))
```

See [itertools/groupby.md](itertools/groupby.md) for the sort-first pattern.

---

## `attrgetter` — object attribute access

```python
from operator import attrgetter

attrgetter('salary')              # obj.salary
attrgetter('department.name')     # obj.department.name  — dotted path
attrgetter('dept', 'salary')      # (obj.dept, obj.salary)
```

Dotted paths are the killer feature — no clean lambda equivalent for deep nesting:

```python
employees.sort(key=attrgetter('salary'))
employees.sort(key=attrgetter('department.headcount'))  # nested object
employees.sort(key=attrgetter('department', 'salary'))  # composite
```

---

## `methodcaller` — method call with fixed arguments

```python
from operator import methodcaller

methodcaller('upper')                 # obj.upper()
methodcaller('strftime', '%Y-%m')     # obj.strftime('%Y-%m')
methodcaller('returns', period='1Y')  # obj.returns(period='1Y')
```

Main use: `map` or sort key where all objects get the same call with the same args:

```python
from datetime import date
dates = [date(2024, 3, 15), date(2024, 1, 1)]
list(map(methodcaller('strftime', '%Y-%m'), dates))
# vs lambda d: d.strftime('%Y-%m')

portfolios.sort(key=methodcaller('returns', period='1Y'))
# vs lambda p: p.returns(period='1Y')
```

For zero-argument methods on built-in types, `str.upper` is cleaner than `methodcaller('upper')`.

---

## When lambdas are still right

Use a lambda when the body involves computation, not just access:

```python
sorted(positions, key=lambda p: p.price * p.quantity)  # arithmetic
sorted(data, key=lambda r: -r['score'])                 # negation
sorted(items, key=lambda x: x.value or 0)              # fallback
```

**Rule:** if the lambda body is only attribute/item/method access (possibly nested or multi-key), use the operator equivalent.

---

## Summary

| | Accesses | Multi-key | Dotted path |
|---|---|---|---|
| `itemgetter` | `obj[key]` | ✓ | ✗ |
| `attrgetter` | `obj.attr` | ✓ | ✓ (`'a.b.c'`) |
| `methodcaller` | `obj.method(*args)` | ✗ | ✗ |

All three: faster than lambda, picklable, work with `sorted`, `min`, `max`, `map`, `groupby`.

See [functools.md](functools.md) for higher-order function patterns that combine well with these.
