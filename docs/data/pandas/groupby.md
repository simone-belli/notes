---
tags:
  - performance
---

# Pandas — GroupBy

## Split–apply–combine

Every `groupby` operation is three steps: **split** rows into groups by key, **apply** a function to each group, **combine** the results. `df.groupby('symbol')` is lazy — it only records how to split and computes nothing until an apply-combine method runs.

```python
g = df.groupby('symbol')   # lazy DataFrameGroupBy, cheap
g.ngroups                  # number of groups
g.get_group('BTC')         # one group's sub-DataFrame
```

`agg`, `transform`, `filter`, and `apply` share the split step and differ only in **what the per-group function returns** — that decides the output shape.

| Method | Function returns | Output shape |
|--------|-----------------|--------------|
| `agg`       | scalar per group | one row per group |
| `transform` | scalar or same-length Series | same shape as input |
| `filter`    | one bool per group | subset of original rows |
| `apply`     | anything | pandas infers |

!!! note "Choosing the verb"
    One number per group → **`agg`**. Same rows back, enriched with a group stat → **`transform`**. Drop/keep whole groups → **`filter`**. None of the above → **`apply`**.

## Grouping by multiple columns

Pass a **list** of keys — the groups are then the distinct combinations of those columns (a cartesian split), and the result carries a **MultiIndex** with one level per key.

```python
df.groupby(['symbol', 'venue'])['close'].mean()   # MultiIndex (symbol, venue) → mean
df.groupby(['symbol', 'venue']).size()             # rows per combination
```

- The key order sets the MultiIndex level order (and the sort order, unless `sort=False`).
- `as_index=False` returns the keys as plain columns instead — a flat, tabular result that's easier to chain or merge.
- Reshape the MultiIndex result with [`.unstack('venue')`](reshaping.md) to pivot the last key into columns, or `.reset_index()` to flatten.
- Select or aggregate a single level afterwards with `level=`: `g.mean().mean(level='symbol')`, or better `df.groupby(level='symbol')` on an already-MultiIndexed frame.

```python
(df.groupby(['symbol', 'venue'], as_index=False)
   .agg(avg_close=('close', 'mean'), n=('close', 'count')))   # tidy 4-column table
```

!!! tip "Keys can be more than column names"
    A groupby key can be a column label, a list of labels, a Series/array of the same length (group by a derived value), an index level name, or a `pd.Grouper`. Mix them freely: `df.groupby(['symbol', df['ts'].dt.hour])`.

## `agg` — reduce each group to a scalar

Builds a **summary table**: one row per group.

```python
df.groupby('symbol')['close'].mean()          # Series
df.groupby('symbol').agg({'close': 'mean', 'volume': ['sum', 'max']})

# Named aggregation (preferred) — flat, self-documenting columns
df.groupby('symbol').agg(
    avg_close=('close', 'mean'),
    total_vol=('volume', 'sum'),
    n=('close', 'count'),
)
```

Named aggregation (`output=('col', 'func')`, pandas ≥ 0.25) avoids the MultiIndex columns the list/dict forms produce — best inside a chain.

!!! warning "Prefer string reducers over lambdas"
    Built-in names (`'sum'`, `'mean'`, `'count'`) dispatch to Cython group loops (fast path). An equivalent `lambda s: s.sum()` runs once per group in Python (slow path) — often 10–100× slower on many small groups.

### Built-in reducers (Cython fast path)

Pass any of these as a string to `agg` (or call as a method on the GroupBy) to stay on the fast path:

- **Counts:** `count` (non-null), `size` (all rows incl. `NaN`), `nunique` (distinct non-null).
- **Sums/products:** `sum`, `prod`.
- **Central/spread:** `mean`, `median`, `std`, `var`, `sem`, `quantile`.
- **Extremes/positions:** `min`, `max`, `idxmin`, `idxmax`, `first`, `last`, `nth`.
- **Boolean:** `any`, `all`.

**Count distinct** is `nunique` — there is no `count_distinct`:

```python
df.groupby('symbol')['venue'].nunique()                 # distinct venues per symbol
df.groupby('symbol').agg(n_venues=('venue', 'nunique')) # named, inside agg
```

!!! note "`count` vs `size` vs `nunique`"
    `count` = non-null values, `size` = every row (nulls included), `nunique` = distinct non-null values. `nunique(dropna=False)` counts `NaN` as one of the distinct values.

## `transform` — broadcast a group stat back to every row

Attaches a group-level statistic to each row (de-mean, z-score, share of total, group-wise NA fill). Returns a scalar (broadcast to group length) or a same-length Series, realigned to the original index.

```python
df['grp_mean'] = df.groupby('symbol')['close'].transform('mean')
df['z']    = df.groupby('symbol')['close'].transform(lambda s: (s - s.mean()) / s.std())
df['pct']  = df['volume'] / df.groupby('symbol')['volume'].transform('sum')
```

`transform` = `agg` **then** merge the summary back onto the original rows, in one step. Cumulative/window methods (`cumsum`, `rank`, `shift`, `ffill`) are already transform-shaped and callable directly: `g['close'].cumsum()`.

## `filter` — keep or drop whole groups

Row filtering at **group** granularity. The callback gets each sub-DataFrame and returns one bool; failing groups are dropped entirely.

```python
df.groupby('symbol').filter(lambda gdf: len(gdf) >= 100)      # drop thin groups
df.groupby('symbol').filter(lambda gdf: gdf['close'].mean() > 50)
```

For per-**row** selection using a group stat, use `transform` and mask instead:

```python
df[df.groupby('symbol')['close'].transform('mean') > 50]
```

## `apply` — general escape hatch

Gets the whole sub-DataFrame and may return a scalar, Series, or DataFrame; pandas guesses how to combine. Flexible but slow (Python call per group) and less predictable — reach for it only when the operation needs the whole group frame.

```python
df.groupby('symbol').apply(lambda gdf: gdf.nlargest(2, 'close'))   # top-2 rows per group
```

## Common keywords

- `as_index=False` — keep group keys as columns instead of the index (like a trailing `.reset_index()`); handy in chains.
- `dropna=False` — keep `NaN` keys as their own group (dropped by default).
- `observed=True` — with Categorical keys, only groups that actually appear (else you get all-`NaN` rows for unused categories).
- `sort=False` — preserve first-appearance order, slightly faster.
- `df.groupby('k').size()` — rows per group; `pd.Grouper(key='ts', freq='1D')` — time-bucket like `resample`.
