# Pandas — Filtering

Two different operations hide behind "filter with a condition", and pandas gives them different verbs:

| Intent | Verb | Result |
|--------|------|--------|
| Keep only matching rows | `df[mask]`, `df.loc[mask]`, `df.query(...)` | fewer rows |
| Keep the shape, blank out non-matching cells | `df.where(cond)`, `df.mask(cond)` | same shape |

```python
import pandas as pd

df = pd.DataFrame({'a': [1, 5, 9], 'b': [10, 20, 30]})

df[df['a'] > 4]        # 2 rows
df.where(df['a'] > 4)  # 3 rows; row 0 becomes NaN, ints upcast to float
```

!!! note "Subset vs replace"
    `df[mask]` **selects** — the frame shrinks and keeps its original index labels. `where`/`mask` **replace element-wise** — the frame keeps its shape and every non-matching cell becomes `NaN` (or `other`). Reach for `where` when the result must stay aligned with the original.

## Building the mask

A mask is a boolean Series aligned to the index.

```python
df['a'] > 4
df['status'].isin(['open', 'new'])   # the SQL IN
df['a'].between(2, 8)                # inclusive by default
df['name'].str.startswith('x')
df['a'].isna()  /  df['a'].notna()
```

Combine with `&`, `|`, `~` — **never** `and`, `or`, `not`:

```python
df[(df['a'] > 4) & (df['b'] < 25)]
df[~df['status'].isin(['closed'])]
```

`and`/`or` call `bool()` on a Series, which raises `ValueError: The truth value of a Series is ambiguous`. The bitwise operators are overloaded to broadcast element-wise instead.

!!! warning "Parentheses are mandatory"
    `&` binds tighter than `>`, so `df['a'] > 4 & df['b'] < 25` parses as `df['a'] > (4 & df['b']) < 25`. Always wrap each comparison.

[`.query()`](transforming/chaining.md) sidesteps both traps by taking a string, where `and`/`or` and normal precedence apply:

```python
cutoff = 4
df.query('a > @cutoff and b < 25')   # @ = Python variable
```

## Subsetting rows

```python
df[df['a'] > 4]              # rows only
df.loc[df['a'] > 4, ['a']]   # rows and columns in one step
df.loc[df['a'] > 4, 'a'] = 0 # the only correct way to *write*
```

- Filtering preserves the original index labels; add `.reset_index(drop=True)` to renumber.
- For assignment always use `.loc` — `df[mask]['a'] = 0` writes into a temporary that may be a copy. See [indexing, views and copies](indexing.md).

## `where` and `mask`

```python
s.where(cond)          # keep where True, else NaN
s.where(cond, other)   # keep where True, else `other`
s.mask(cond, other)    # exact inverse — replace where True
```

`mask(cond)` is `where(~cond)`; pick whichever reads positively. `other` may be a scalar, a Series/DataFrame (aligned on the index), or a callable:

```python
df['a'].where(df['a'] > 0, 0)                  # floor negatives at 0
df['a'].where(df['a'] > 0, df['b'])            # fall back to another column
df['a'].where(df['a'] < 100, lambda s: s / 2)  # callable receives the original
```

### `Series.where` vs `np.where`

```python
import numpy as np

df['flag'] = np.where(df['a'] > 4, 'big', 'small')
```

`np.where(cond, x, y)` is a plain ternary over arrays: both branches required, returns a bare NumPy array with no index. Use it to build a new column from a two-way condition; use `Series.where` to *preserve* the existing values on one side and stay index-aligned. For more than two branches, use `np.select` or `pd.cut`.

## Missing values in masks

Comparisons against `NaN` return `False`, so those rows drop out of `df[mask]` — which means `df[m]` and `df[~m]` do **not** partition a frame whose column has nulls.

With [nullable dtypes](dtypes.md) (`Int64`, `boolean`) the comparison yields `pd.NA` and boolean indexing raises `ValueError: Cannot mask with non-boolean array containing NA / NaN values`. Decide explicitly what a null means:

```python
df[(df['a'] > 4).fillna(False)]
```

## Performance

- Masks are vectorised — one C-level pass, far faster than `apply` or a Python loop.
- `df[m1][m2]` materialises an intermediate frame; `df[m1 & m2]` does one pass. Prefer the combined mask.
- `.query()` can dispatch to `numexpr` on large frames (roughly >10k rows), avoiding intermediate boolean arrays.
- On a sorted index, `.loc` slicing beats a mask.
