# Pandas — MultiIndex

A **MultiIndex** (hierarchical index) is an index whose labels are **tuples**: a row keyed `('AAPL', '2024-01-02')` instead of a single value. Each tuple position is a **level** (optionally named). You don't create them by hand much — [reshaping](transforming/reshaping.md) and [grouping](transforming/groupby.md) *produce* them — so the goal is just to select from and flatten them without fear.

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

## Adding a level

Adding a level means every key `k` becomes `(new, k)` or `(k, new)` — the data body is untouched. The tool depends on where the new label comes from.

```python
# From an existing column — lands INNERMOST
df.set_index('symbol', append=True)          # append=True keeps the current index
df.assign(scenario='base').set_index('scenario', append=True)   # constant, chain-friendly

# A constant tag — lands OUTERMOST
pd.concat([df], keys=['base'], names=['scenario'])
pd.concat([base, stress], keys=['base', 'stress'], names=['scenario'])  # the general form

# From a computed array — rebuild the index
df.index = pd.MultiIndex.from_arrays([['base'] * len(df), df.index],
                                     names=['scenario', 'date'])

# On the COLUMNS axis — namespace the columns
df.columns = pd.MultiIndex.from_product([['prices'], df.columns])
```

- `from_arrays` (parallel label arrays), `from_tuples` (you already have the tuples), `from_product` (Cartesian grid).
- `set_index` consumes the column; pass `drop=False` to keep a copy in the body.

!!! warning "Position and sortedness"
    `set_index(append=True)` puts the new level **innermost**, `concat(keys=)` **outermost** — fix with `swaplevel`/`reorder_levels`. Either way the index is usually no longer lexicographically sorted, so follow with `.sort_index()` before slicing. Unnamed levels can only be addressed by integer position, so always pass `names=`.

## Rearranging and flattening levels

```python
df.swaplevel('symbol', 'date')            # reorder two levels
df.reorder_levels(['date', 'symbol'])
df.droplevel('symbol')                    # delete a level
df.rename_axis(index={'symbol': 'ticker'})  # rename a level
```

## reset_index and set_index

The inverse pair: `reset_index` moves index levels **into the body** as columns, `set_index(append=True)` moves columns **back into the index**.

```python
df.reset_index()                    # all levels → columns, fresh RangeIndex
df.reset_index(level='symbol')      # just one level → column, rest stays indexed
df.reset_index(level=['symbol', 'date'])
df.reset_index(level=0)             # by position

df.set_index('symbol', append=True) # the opposite — column back into the index
```

A full round trip:

```python
flat  = mi_df.reset_index(level='symbol')       # symbol becomes a column
mi_df = flat.set_index('symbol', append=True)   # …and back
```

- `reset_index(drop=True)` **discards** the level instead of moving it — the same effect as `droplevel` for a MultiIndex, but it also resets a single index to a `RangeIndex`.
- Unnamed levels become columns called `level_0`, `level_1`, …; name them first with `rename_axis` to control the result.
- On a Series, `reset_index()` returns a **DataFrame**; pass `name=` to label the value column. `reset_index(drop=True)` keeps it a Series.
- If the columns are themselves a MultiIndex, `col_level=` picks which column level the new names land on and `col_fill=` fills the others.

!!! warning "The round trip does not preserve level order"
    `reset_index` inserts the freed levels as the **leftmost columns**, in level order; `set_index(append=True)` puts them back **innermost**. Reordering more than one level at a time needs `reorder_levels` afterwards — and `.sort_index()` before you slice again.

!!! tip "Two axes, two verbs"
    `set_index`/`reset_index` move labels between the **index and the data body**; [`stack`/`unstack`](transforming/reshaping.md) move levels between the **row and column axes**. When a MultiIndex is more trouble than it's worth, `reset_index()` is the escape hatch back to the long shape and ordinary [column filtering](filtering.md).
