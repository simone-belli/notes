---
quiz: core
---

# Method Chaining

## Method chaining

Instead of reassigning `df` repeatedly, chain operations that each return a new DataFrame:

```python
result = (
    raw
    .query('price > 0')
    .assign(
        log_price=lambda d: np.log(d['price']),
        returns=lambda d: d['price'].pct_change(),
    )
    .dropna()
    .reset_index(drop=True)
)
```

`raw` is never mutated. Each step is independently readable and commentable.

### `.query(expr)` — filter rows

```python
df.query('age > 18 and city == "London"')
df.query('price > @threshold')   # @ references a Python variable
```

### `.assign(**kwargs)` — add or overwrite columns

```python
df.assign(
    income_k=lambda d: d['income'] / 1_000,
    is_high_earner=lambda d: d['income_k'] > 50,   # can reference columns assigned above
)
```

Lambdas receive the DataFrame *as it is at that step*. Columns added earlier in the same call are visible to later ones (dict ordering, Python 3.7+). Assign `None` to drop a column.

### `.pipe(func, *args, **kwargs)` — apply a named function mid-chain

```python
def trim_outliers(df, col, n_std=3):
    lo, hi = df[col].mean() - n_std*df[col].std(), df[col].mean() + n_std*df[col].std()
    return df[df[col].between(lo, hi)]

result = (
    raw
    .assign(returns=lambda d: d['close'].pct_change())
    .pipe(trim_outliers, col='returns', n_std=2.5)
    .dropna()
)
```

`df.pipe(f, ...)` calls `f(df, ...)` — a fluency adapter for functions that don't natively chain. Debug mid-chain: `.pipe(lambda d: (print(d.shape), d)[1])`.

## Common chain operations

Extracted to [chaining-catalog.md](chaining-catalog.md) — a lookup catalog of the ten most-used chain operations (`.astype`, `.rename`, `.filter`, `.sort_values`, `.groupby().agg()`, …) with a full pipeline example.

The same "named, single-purpose step" argument for chaining over nested calls is why SQL favours [CTEs](../../sql/window-functions.md) over nested subqueries.

