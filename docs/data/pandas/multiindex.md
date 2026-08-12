# Pandas — MultiIndex

A **MultiIndex** (hierarchical index) is an index whose labels are **tuples**: a row keyed `('AAPL', '2024-01-02')` instead of a single value. Each tuple position is a **level** (optionally named). You don't create them by hand much — [reshaping](reshaping.md) and [grouping](groupby.md) *produce* them — so the goal is just to select from and flatten them without fear.

## Where they come from

```python
df.groupby(['symbol', 'date'])['ret'].mean()   # 2-level row MultiIndex
df.set_index(['symbol', 'date'])               # promote two columns to a MultiIndex
wide.unstack('symbol')                         # moves a level onto the columns axis
```

## Selecting (the part people fear)

Use `.loc` with **tuples**; use `.xs` to slice a single inner level.

```python
s.loc[('AAPL', '2024-01-02')]      # full key → scalar
s.loc['AAPL']                      # partial key on the OUTER level → sub-Series (level dropped)
s.xs('2024-01-02', level='date')   # slice by an INNER level at any depth
s.loc[(slice(None), '2024-01-02'), :]   # "all symbols, that date"; slice(None) == ":"

idx = pd.IndexSlice
df.loc[idx[:, '2024-01-02'], :]         # IndexSlice — the readable form of the line above
```

- Partial indexing on the **outer** level is easy (`s.loc['AAPL']`). Reaching an **inner** level needs `.xs(..., level=)` or an `IndexSlice` — `s.loc['2024-01-02']` would wrongly try the outer level.
- A **MultiIndex on columns** follows the same rules on the column axis: `df['AAPL']` grabs the outer group; `df.loc[:, ('AAPL', 'ret')]` reaches a leaf.

!!! warning "Sort before you slice"
    Range/partial slicing needs the MultiIndex **lexicographically sorted**, else pandas raises `UnsortedIndexError` (or warns on performance). Call `df.sort_index()` right after building one; `df.index.is_monotonic_increasing` tells you if it's ready.

## Rearranging and flattening levels

```python
df.swaplevel('symbol', 'date')            # reorder two levels
df.reorder_levels(['date', 'symbol'])
df.droplevel('symbol')                    # delete a level
df.rename_axis(index={'symbol': 'ticker'})  # rename a level
df.reset_index()                          # MultiIndex → plain columns (the escape hatch)
df.reset_index(level='symbol')            # move just one level back to a column
```

!!! tip "`reset_index` is the escape hatch"
    When a MultiIndex is more trouble than it's worth, `reset_index()` flattens it to ordinary columns (the long shape) and you're back on familiar ground. `set_index`/`reset_index` move labels between the axes and the data body; [`stack`/`unstack`](reshaping.md) move levels between the row and column axes — same operation, different view.
