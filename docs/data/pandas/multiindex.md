# Pandas — MultiIndex

A **MultiIndex** (hierarchical index) is an index whose labels are **tuples**: a row keyed `('AAPL', '2024-01-02')` instead of a single value. Each tuple position is a **level** (optionally named). You don't create them by hand much — [reshaping](transforming/reshaping.md) and [grouping](transforming/groupby.md) *produce* them — so the goal is just to select from and flatten them without fear.

## Where they come from

```python
df.groupby(['symbol', 'date'])['ret'].mean()   # 2-level row MultiIndex
df.set_index(['symbol', 'date'])               # promote two columns to a MultiIndex
wide.unstack('symbol')                         # moves a level onto the columns axis
```

## Selecting (the part people fear)

Two rules remove most of the difficulty:

1. **Use the two-argument form** — `df.loc[rowkey, colkey]`, never `df.loc[key]` on a DataFrame.
2. **Tuple = one key, list = many keys.** `('AAPL', '2024-01-02')` is a single point in the hierarchy; `['AAPL', 'MSFT']` is two outer-level keys.

```python
idx = pd.IndexSlice

# exact
df.loc[('AAPL', '2024-01-02'), :]        # one full key → the row
df.loc[('AAPL', '2024-01-02'), 'ret']    # one cell (.at is the faster scalar form)
df.loc[[('AAPL', '2024-01-02'), ('MSFT', '2024-01-03')], :]   # several full keys

# partial, OUTER level
df.loc['AAPL']                           # sub-frame, outer level DROPPED
df.loc[['AAPL', 'MSFT'], :]              # several outer keys, level KEPT
df.loc['AAPL':'MSFT', :]                 # label range on the outer level

# INNER level
df.xs('2024-01-02', level='date')        # level dropped; drop_level=False keeps it
df.xs(('AAPL', '2024-01-02'), level=('symbol', 'date'))   # several levels at once

# combining across levels
df.loc[idx[:, '2024-01-02'], :]          # all symbols, that date
df.loc[idx['AAPL':'MSFT', :], ['ret']]
```

- Partial indexing on the **outer** level is easy (`df.loc['AAPL']`). Reaching an **inner** level needs `.xs(..., level=)` or an `IndexSlice` — `df.loc['2024-01-02']` would wrongly try the outer level.
- `slice(None)` is the literal spelling of `:` inside a tuple: `df.loc[(slice(None), '2024-01-02'), :]`. `pd.IndexSlice` exists purely so you can write `:` instead.
- `.iloc` is untouched by any of this — it stays purely positional.

!!! warning "A tuple in `.loc` is ambiguous with (row, column)"
    Pandas tries the tuple as a **full row key** first and falls back to **`(row, column)`** only if that fails — so the meaning depends on your data. With a `ret` column, `df.loc[('AAPL', 'ret')]` returns a *column* slice, while `df.loc[('AAPL', '2024-01-02')]` returns a *row*. Writing `df.loc[('AAPL', 'ret'), :]` states which you meant.

### Masks: the escape hatch

```python
df[df.index.get_level_values('symbol') == 'AAPL']
df.query("symbol == 'AAPL' and ret > 0")     # named levels are visible to query
```

`get_level_values` returns a flat Index of that level's labels, one per row, so any ordinary [boolean mask](filtering.md) works — `.isin`, `.str` methods, comparisons against a column. It needs no sorting and never hits the tuple ambiguity. When `.loc` gymnastics stop being readable, use this.

### Hierarchical columns

The same rules, one axis over:

```python
c['ret']                                # outer group → sub-frame
c.loc[:, ('ret', 'AAPL')]               # leaf → Series
c.loc[:, idx[:, 'AAPL']]                # one inner label across all outer groups
c.xs('AAPL', axis=1, level='symbol')    # ditto, flattened
```

!!! warning "Sort before you slice"
    Range and `IndexSlice` slicing need the MultiIndex **lexicographically sorted**, else pandas raises `UnsortedIndexError: MultiIndex slicing requires the index to be lexsorted`. Exact-key lookup is unaffected. Call `df.sort_index()` right after building one; `df.index.is_monotonic_increasing` tells you if it's ready.

Assignment addresses the frame identically — `df.loc[idx[:, '2024-01-02'], 'flag'] = True`. Keep the two-argument form here too, since chained assignment (`df.loc['AAPL']['ret'] = ...`) silently fails to write through; see [indexing](indexing.md).

## Adding a level

Adding a level means every key `k` becomes `(new, k)` or `(k, new)` — the data body is untouched. The tool depends on where the new label comes from.

### On the rows

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
```

- `from_arrays` (parallel label arrays), `from_tuples` (you already have the tuples), `from_product` (Cartesian grid).
- `set_index` consumes the column; pass `drop=False` to keep a copy in the body.

### On the columns

Wrapping flat columns under one constant label — `'a'` → `('prices', 'a')` — is how you namespace a frame before gluing it next to another (see [merge](transforming/merge.md) for `concat` vs key-matching joins). Two frames that both have an `AAPL` column can then sit side by side, and `wide['prices']` peels the level back off.

```python
# General — the only form that also works on already-nested columns
pd.concat([df], keys=['prices'], axis=1, names=['group'])

# Terse — rebuilds the index from scratch, so restate every level name
df.columns = pd.MultiIndex.from_product([['prices'], df.columns],
                                        names=['group', 'field'])

df.columns = pd.MultiIndex.from_product([df.columns, ['base']])  # innermost instead
df.columns = df.columns.droplevel(0)                             # undo
```

- `names=['group']` on `concat` names only the **new** level; an existing `df.columns.name` carries through untouched.
- `from_product` silently breaks on columns that are already a MultiIndex: `[['base'], mi_cols]` yields `('base', ('prices', 'a'))` — a tuple *as a label*, not two levels.
- Assigning `df.columns = ...` mutates in place; `concat` returns a new frame, so it chains.

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
