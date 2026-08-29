---
tags:
  - performance
---

# Pandas — Apply

`DataFrame.apply` runs a function that takes a **Series** over every column (or every row) of a frame. Two things determine the result: the `axis` argument, which decides what the Series *is*, and what the function returns, which decides the output shape.

```python
import pandas as pd

def zscore(s: pd.Series) -> pd.Series:
    return (s - s.mean()) / s.std()

def span(s: pd.Series) -> float:
    return s.max() - s.min()
```

## `axis` picks columns or rows

```python
df.apply(zscore)           # axis=0 (default) — f gets each column
df.apply(span, axis=1)     # f gets each row, indexed by column labels
```

- `axis=0` — one call per **column**; the Series is indexed by the row index, `.name` is the column label.
- `axis=1` — one call per **row**; the Series is indexed by the column labels.

!!! tip "The axis is a direction, not the object you get"
    `axis=0` means *move down the rows*, which hands you a column — same convention as `df.sum(axis=0)` giving per-column totals. The axis names what gets collapsed, never what `f` receives.

With `axis=1` the row Series takes the **common dtype** of that row: a frame mixing `int64` and `str` yields `object` Series, and arithmetic inside `f` quietly drops to Python speed.

## Return shape decides output shape

| `f` returns | `df.apply(f)` | `df.apply(f, axis=1)` |
|---|---|---|
| scalar | Series indexed by column labels | Series indexed by row labels |
| Series | DataFrame, same columns | DataFrame, columns from returned index |

```python
df.apply(span)      # Series: one number per column
df.apply(zscore)    # DataFrame: same shape as df
```

For `axis=1`, `result_type=` disambiguates a list/Series return: `'expand'` spreads it into columns, `'reduce'` keeps one object Series, `'broadcast'` fills back into the original columns.

```python
df.apply(lambda r: [r.hi, r.lo], axis=1, result_type='expand')   # 2 columns
```

## Choosing between apply, agg, transform, pipe, map

- **`apply(f)`** — per column/row, any return shape.
- **`agg(f)`** — reductions, and the only one taking a list or dict: `df.agg(['mean', span])`, `df.agg({'close': 'mean', 'volume': span})`.
- **`transform(f)`** — per column/row but *requires* same-shape output; raises `ValueError` if `f` reduces. Use when shape preservation is the contract. Same distinction as in [groupby](groupby.md).
- **`pipe(f)`** — the whole frame, once; for `DataFrame -> DataFrame` functions. See [method chaining](chaining.md).
- **`map(f)`** — element-wise, one scalar per call. Renamed from `applymap` in pandas 2.1 (`applymap` is deprecated).

## Try `f(df)` first

Most Series functions built from operators and Series methods work on a DataFrame unchanged, because DataFrame implements the same operators column-wise:

```python
zscore(df)      # works, fully vectorised — no apply needed
```

NumPy universal functions (ufuncs) apply directly too: `np.log(df)`. Reserve `apply` for functions using Python control flow, a non-vectorised library, or the Series' `.name`.

!!! warning "`axis=1` builds a Series per row"
    Column-wise apply loops over a handful of columns, so overhead is negligible. Row-wise apply loops over every row, constructing a temporary Series each time — that construction, not your function, is usually the bottleneck. Express row logic as column arithmetic (`np.where`, boolean masks) where possible; see the [performance hierarchy](../iteration.md#performance-hierarchy).

On an **empty** frame `apply` still calls `f` once on an empty Series to infer the dtype — guard `f` if it can't handle that.
