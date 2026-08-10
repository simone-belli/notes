---
quiz: detail
---

# `itertools` filtering

All five are lazy iterators that select or reject elements from a stream. `filter` is a builtin; the rest live in `itertools`.

See [core.md](core.md) for `chain`, `islice`, `product`, `combinations`.

---

## filter and filterfalse — predicate-based selection

```python
from itertools import filterfalse

list(filter(lambda x: x % 2 == 0, range(8)))       # → [0, 2, 4, 6]
list(filterfalse(lambda x: x % 2 == 0, range(8)))  # → [1, 3, 5, 7]

filter(None, iterable)      # keep truthy values (None as predicate)
```

- `filter(f, it)` ≡ `(x for x in it if f(x))`
- `filterfalse(f, it)` ≡ `(x for x in it if not f(x))`
- Together they **partition** a stream:

```python
items = list(iterable)
yes = filter(pred, items)
no  = filterfalse(pred, items)
```

---

## compress — mask-style filter

Keeps `data[i]` where `selectors[i]` is truthy. Stops at the shorter iterable.

```python
from itertools import compress

data      = ['A', 'B', 'C', 'D', 'E']
selectors = [1,    0,   1,   0,   1  ]
list(compress(data, selectors))   # → ['A', 'C', 'E']
```

- Equivalent to `(d for d, s in zip(data, selectors) if s)`.
- The lazy analog of NumPy boolean indexing — use it when the mask is precomputed separately:

```python
signal   = compute_buy_signal(prices)   # list of bools
buy_days = list(compress(dates, signal))
```

!!! warning "Silent truncation"
    If `data` and `selectors` have different lengths, `compress` silently stops at the shorter one with no error.

---

## takewhile — yield from the front, stop on first failure

```python
from itertools import takewhile

list(takewhile(lambda x: x < 5, [1, 3, 4, 6, 1, 2]))
# → [1, 3, 4]   — stops at 6; the trailing 1, 2 are never yielded
```

Once the predicate returns False for one element, iteration stops **permanently** — even if later elements would match again.

!!! note "Ordered data only"
    `takewhile` only makes sense when the condition holds for a contiguous prefix (sorted data, timestamps, etc.). Use `filter` for scattered matches.

---

## dropwhile — skip the prefix, yield the tail

```python
from itertools import dropwhile

list(dropwhile(lambda x: x < 5, [1, 3, 4, 6, 1, 2]))
# → [6, 1, 2]   — drops 1, 3, 4; yields everything from 6 onward
```

After the first element where the predicate is False, `dropwhile` switches to **yield-all** mode — it does **not** re-test remaining elements.

```python
# Skip a 20-day warm-up period before computing signals
warmed_up = dropwhile(lambda r: r.day < 21, data_rows)
```

---

## At a glance

| Function | Scans all? | Use when |
|---|---|---|
| `filter(f, it)` | yes | predicate, scattered matches |
| `filterfalse(f, it)` | yes | complement of filter |
| `compress(data, sel)` | yes (shortest) | mask already computed |
| `takewhile(f, it)` | no (stops early) | contiguous prefix, ordered data |
| `dropwhile(f, it)` | no (skips prefix) | skip head, keep tail |

!!! tip "filter vs takewhile"
    `filter` scans the whole stream and picks matching elements anywhere. `takewhile` reads only until the first failure — use it to avoid consuming a long or infinite stream unnecessarily.