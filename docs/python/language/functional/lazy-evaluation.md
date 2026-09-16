---
tags:
  - performance
quiz: detail
---

# Lazy vs Eager Evaluation

**Eager**: compute everything now, store the full result in memory.  
**Lazy**: produce one element at a time, on demand; O(1) memory regardless of input size.

```python
eager = [x * 2 for x in range(1_000_000)]   # allocates ~8 MB immediately
lazy  = (x * 2 for x in range(1_000_000))   # 104 bytes — a state machine
```

## Python's lazy built-ins

`range`, `map`, `filter`, `zip`, `enumerate`, `reversed`, `dict.keys/values/items`, generator expressions, and all of `itertools` are lazy. List/dict/set comprehensions are eager.

!!! warning "A generator can only be iterated once — after that it's exhausted"
    Once consumed, a generator yields nothing. Calling `list(gen)` twice returns an empty list the second time. If you need multiple passes (sorting, two separate loops), materialise to a list first with `data = list(gen)`.

## Forcing evaluation ("sinks")

A lazy iterator does nothing until consumed:

```python
gen = (x * 2 for x in range(10))

list(gen)   # materialise to list
sum(gen)    # fold to scalar — never builds a list; O(1) memory
max(gen)    # same
next(gen)   # pull one element
```

`sum()` and `max()` are the best sinks when you only need a scalar — they stream through the iterator without ever allocating the intermediate collection.

## When lazy wins

**Large data, single pass** — don't load what you don't need:

```python
total = sum(
    float(line.split(",")[3])
    for line in open("trades.csv")
    if line.startswith("2024")
)
```

**Short-circuiting** — stops as soon as the answer is known:

```python
found = any(is_breached(pos) for pos in portfolio)   # stops at first True
first_loss = next(t for t in trades if t.pnl < 0)   # pulls one element
```

With an eager list comprehension both would evaluate every element first.

**Infinite sequences** — impossible to materialise:

```python
from itertools import count, islice
first_10_evens = list(islice(count(0, 2), 10))
```

**Pipeline composition** — chain lazy stages with no intermediate allocations:

```python
from itertools import islice

result = list(islice(
    (float(row["pnl"]) for row in load_trades("trades.csv") if row["desk"] == "eq"),
    500,
))
```

Each stage hands one element at a time to the next. Memory = sum of stage state, not data size.

!!! tip "sum() and max() are the best sinks — they stream without allocating"
    `list(gen)` and `sum(gen)` both consume the generator, but `list` allocates O(n) memory first. `sum(gen)` and `max(gen)` maintain O(1) state (a running total or current max), streaming through without ever building the intermediate collection. Prefer them when you only need a scalar result.

## When eager wins

| Need | Why lazy fails | Use |
|------|---------------|-----|
| Multiple passes | iterator exhausted after one | `list()` first |
| Random access (`data[i]`) | iterators don't index | `list()` |
| `len()` | generators have no length | `list()` or count separately |
| Sorting | must consume fully anyway | `sorted()` |
| Numerical computation | Python-loop overhead | NumPy / Pandas (vectorised) |

NumPy and Pandas are always eager — they allocate upfront and run vectorised C operations. That tradeoff (memory for speed) is correct when the data fits in RAM and you're doing numerical work.

```python
import numpy as np

# NumPy — eager, but vectorised and much faster
nav = np.cumprod(1 + returns)

# Pure-Python lazy — O(1) memory, but a Python loop per element
from itertools import accumulate
import operator
nav = list(accumulate((1 + r for r in returns), operator.mul))
```

## Generator function vs generator expression

Both are lazy. Use a function when logic is multi-step or stateful:

```python
# Expression — fine for simple transforms
pos_returns = (r for r in daily_returns if r > 0)

# Function — needed when local state spans yields
def period_returns(prices):
    prev = None
    for p in prices:
        if prev is not None:
            yield (p - prev) / prev
        prev = p
```

## Summary

| | Lazy | Eager |
|---|---|---|
| Memory | O(1) | O(n) |
| Multiple passes | No (exhausted) | Yes |
| Random access | No | Yes |
| Short-circuit | Yes | No |
| Infinite sequences | Yes | No |
| Numeric speed | Slow (Python loop) | Fast (vectorised) |

## Related

- [iterators-generators.md](iterators-generators.md) — iterator protocol, `yield`, generator functions
- [itertools/core.md](itertools/core.md) — lazy combinatorics: `chain`, `islice`, `product`
- [itertools/accumulate.md](itertools/accumulate.md) — lazy running totals; vs `numpy.cumsum`
