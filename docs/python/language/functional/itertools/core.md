---
quiz: detail
---

# `itertools`

All four operate on *iterators* — they are lazy and never materialise the full sequence in memory. This matters when your input is a tick stream, a 5000-ticker universe, or a cross of many scenario axes.

See [groupby.md](groupby.md) for `groupby` and [accumulate.md](accumulate.md) for running totals.

---

## `chain` — concatenate iterables into one stream

```python
from itertools import chain

chain(iter_a, iter_b, iter_c)       # one after another
chain.from_iterable(list_of_iters)  # flatten one level
```

- Use `chain.from_iterable` when the outer iterable is itself a generator (can't unpack with `*`).

**Financial examples:**
```python
# Merge trade logs from multiple desks
all_trades = chain(equity_trades, fx_trades, rates_trades)
total_pnl = sum(t.pnl for t in all_trades)

# Flatten per-account transaction lists
transactions = chain.from_iterable(account_txns.values())

# Prepend a header row to a report generator
rows = chain([header], generate_report_rows())
```

---

## `islice` — slice a lazy iterator

```python
from itertools import islice

islice(iterable, stop)
islice(iterable, start, stop)
islice(iterable, start, stop, step)
```

Like list slicing but for iterators, which don't support `[start:stop]`. Consumes only what it needs; the rest is untouched.

- Does **not** support negative indices — use `collections.deque(it, maxlen=N)` for last-N.

**Financial examples:**
```python
# Top-20 holdings from a sorted generator
top20 = list(islice(rank_by_momentum(universe), 20))

# Skip a 21-day warm-up period
returns_ex_warmup = islice(daily_returns, 21, None)

# Page through large API results
def paginate(gen, page_size=100):
    while chunk := list(islice(gen, page_size)):
        process(chunk)
```

---

## `product` — Cartesian product (scenario grids)

```python
from itertools import product

product(A, B)        # all (a, b) pairs — equivalent to nested for loops
product(A, repeat=k) # all k-tuples drawn from A
```

`product(A, B, C)` is exactly `[(a,b,c) for a in A for b in B for c in C]`, but lazy.

**Financial examples:**
```python
rate_shocks   = [-0.01, 0.00, +0.01, +0.02]
spread_shocks = [-0.005, 0.00, +0.005]
vol_shocks    = [0.8, 1.0, 1.2]

# All 4 × 3 × 3 = 36 stress scenarios
for dr, ds, dv in product(rate_shocks, spread_shocks, vol_shocks):
    price_scenario(portfolio, dr, ds, dv)

# Grid search over model hyperparameters
for lookback, threshold in product(range(10, 60, 5), [0.01, 0.02, 0.05]):
    backtest(lookback, threshold)
```

---

## `combinations` — unordered subsets without repetition

```python
from itertools import combinations, combinations_with_replacement

combinations(pool, r)                  # C(n, r) subsets, no repeats
combinations_with_replacement(pool, r) # allows repeated elements
```

`combinations('ABCD', 2)` → `AB AC AD BC BD CD` — 6 pairs, not 12.

**Financial examples:**
```python
# All pairs for a correlation matrix (avoid computing both (A,B) and (B,A))
for t1, t2 in combinations(tickers, 2):
    corr_matrix[t1][t2] = correlation(returns[t1], returns[t2])

# All 3-stock baskets from a universe of 20 — C(20,3) = 1140
for basket in combinations(universe, 3):
    backtest_basket(basket)
```

---

## `product` vs `combinations`

| | `product` | `combinations` |
|---|---|---|
| Draws from | multiple independent pools | one shared pool |
| Repeats | yes (across pools) | no |
| Order matters | yes | no |
| Use for | scenario grids, hyperparameter search | portfolio subsets, pair selection |

---

## Check size before iterating

!!! warning "Combinatorial explosion: always compute size before enumerating"
    `combinations(universe, 5)` over 500 assets produces 255 billion pairs. Even with lazy iteration, processing each one takes time — this will not finish. Use `math.comb(n, r)` to check the count before writing the loop, and switch to random sampling for large spaces.

```python
from math import comb

print(comb(500, 5))   # 255,244,687,600 — do NOT enumerate
print(4 * 3 * 3)      # 36 — fine
```

If the count is large, switch to random sampling or Monte Carlo instead.

---

## Composing them

All functions consume and return iterators, so they compose directly:

```python
# Top-10 most correlated pairs from all combinations
top_pairs = list(
    islice(
        sorted(
            ((corr(r[a], r[b]), a, b) for a, b in combinations(tickers, 2)),
            reverse=True,
        ),
        10,
    )
)
```

See [../iterators-generators.md](../iterators-generators.md) for the iterator protocol underlying all of these.
