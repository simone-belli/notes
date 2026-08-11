# Pandas — Reshaping

## `stack` / `unstack` — rotate levels between index and columns

`unstack` moves an **index** level out to become **column** labels; `stack` moves a **column** level down into the index. They are inverses, and both are pure relabelling — no values change, nothing is aggregated. Use them to rotate a DataFrame between a **long** shape (info in the index, typically post-`groupby`) and a **wide** shape (info across columns).

```python
s = df.groupby(['symbol', 'venue'])['close'].mean()   # MultiIndexed Series
s.unstack()            # move innermost level ('venue') to columns → DataFrame
s.unstack('venue')     # move a level by name (safer than position)
s.unstack(0)           # move a level by position

wide.stack()           # inverse: innermost column level → index
```

!!! note "The shape invariant"
    `unstack` decreases index depth by one and increases column depth by one; `stack` does the reverse. The total number of label dimensions is conserved — you're only choosing which coordinates count as "row" vs "column".

- Series with a 2-level MultiIndex → `unstack()` → **DataFrame** (one level indexes rows, the moved level becomes columns). The case to memorise.
- DataFrame with MultiIndex rows → `unstack()` → DataFrame with **MultiIndex columns** (existing columns become the outer level). Often followed by `.droplevel()` to flatten.
- `s.unstack().stack()` round-trips (modulo dropped `NaN`s and int→float upcast).

## Missing combinations → `NaN`

Unstacking forms the **cartesian product** of the remaining index and the new columns. Combinations absent from the data become `NaN`, which silently upcasts integer columns to float. Supply `fill_value=` to avoid both:

```python
s.unstack(fill_value=0)
```

`stack` does the opposite by default — it **drops** empty cells; `stack(dropna=False)` keeps them.

!!! warning "Duplicate entries can't be unstacked"
    If the `(remaining-index, unstacked-level)` pair isn't unique, `unstack` raises `ValueError: Index contains duplicate entries, cannot reshape`. You need to aggregate first — use a `groupby().agg()` or reach for `pivot_table`.

## The canonical workflow: groupby → unstack

Most `unstack` usage turns a multi-key aggregation into a readable matrix:

```python
(df.groupby(['symbol', 'venue'])['close'].mean()
   .unstack('venue'))
# venue    binance  kraken
# symbol
# BTC        100.0   101.0
# ETH         40.0    41.0

wide['kraken'] - wide['binance']   # cross-venue math is now column arithmetic
```

This is functionally the same as `pivot_table(index='symbol', columns='venue', values='close', aggfunc='mean')`. `unstack` is the low-level primitive; `pivot`/`pivot_table` are the declarative front doors. See [groupby.md](groupby.md) for the multi-key grouping that produces the MultiIndex.

## `unstack` vs `pivot` vs `pivot_table` vs `melt`

All rearrange between long and wide; pick by what you start from and whether you must aggregate.

| Tool | Operates on | Aggregates? | Reach for it when |
|------|-------------|-------------|-------------------|
| `unstack` / `stack` | the **index** (MultiIndex) | no | you already have a MultiIndex (usually post-groupby) and just want to rotate a level |
| `pivot` | **columns** of a flat frame | no — errors on duplicate index/col pairs | tidy long → wide, one row per index/column combo guaranteed |
| `pivot_table` | columns of a flat frame | **yes** (`aggfunc`) | long → wide *with* duplicates to reduce; spreadsheet-style pivot |
| `melt` | columns of a wide frame | no | wide → long ("unpivot"), the inverse of `pivot` |

Rule of thumb: if the data is **already indexed** the way you want, use `stack`/`unstack`. If you start from flat columns and want to name index/columns/values, use `pivot`/`pivot_table`. Both `stack` and `melt` go wide→long — `stack` works on the column *index*, `melt` on named columns. All of these rearrange **one** frame; to combine **two** frames on a key, use [merge.md](merge.md).

```python
df.pivot(index='date', columns='symbol', values='close')                 # no aggregation
df.pivot_table(index='date', columns='symbol', values='close', aggfunc='mean')
df.melt(id_vars='date', var_name='symbol', value_name='close')           # wide → long
```
