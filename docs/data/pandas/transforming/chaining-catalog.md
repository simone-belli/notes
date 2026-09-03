# Chain Operations — Catalog

Lookup catalog of the operations most used in method chains. For the chaining concept itself (`.query`, `.assign`, `.pipe`), see [chaining.md](chaining.md).

| # | Method | What it does |
|---|--------|-------------|
| 1 | `.query(expr)` | Filter rows |
| 2 | `.assign(**kwargs)` | Add or transform columns |
| 3 | `.astype(dict)` | Cast dtypes |
| 4 | `.rename(columns=...)` / `.rename(name)` | Rename columns, or name a Series |
| 5 | `.drop(columns=[...])` / `.filter(...)` | Remove or select columns |
| 6 | `.sort_values(by=...)` | Sort rows |
| 7 | `.dropna()` / `.fillna(...)` | Handle missing values |
| 8 | `.assign(c=lambda d: d['c'].str...)` | String operations on a column |
| 9 | `.set_index()` / `.reset_index(drop=True)` | Index management |
| 10 | `.groupby().agg(...)` | Aggregate by group |
| 11 | `df[[...]]` / `.reindex(columns=...)` | Reorder columns |
| 12 | `.to_frame(name)` | Series → one-column DataFrame |

## 1. Filter rows — `.query()`

```python
df.query('price > 0 and volume > 1_000')
df.query('status == "active"')
df.query('date > @cutoff')      # @ = Python variable
```

For boolean masks and `where`/`mask`, see [filtering](../filtering.md).

!!! tip "assign() lambdas see columns added earlier in the same call"
    Within one `.assign()` call, `lambda d: ...` receives the DataFrame as it exists at that point — including columns defined by earlier keyword arguments in the same call. This lets you build derived columns in sequence without chaining multiple `.assign()` calls.

## 2. Add / transform columns — `.assign()`

See [chaining.md](chaining.md). Key: lambdas see columns added earlier in the same call.

## 3. Cast dtype — `.astype()`

```python
df.astype({'price': 'float32', 'volume': 'float32', 'trades': 'int32'})
# or inline via assign:
df.assign(price=lambda d: d['price'].astype('float32'))
```

Use `.astype(dict)` for bulk casts; `.assign()` when interleaved with other column ops.

**Low-cardinality string columns** (side, status, country) should be cast to `"category"` — stores integer codes + a lookup table instead of full strings per row. Lower memory, faster `groupby` and `value_counts`.

```python
df.astype({'side': 'category', 'status': 'category'})

# Ordered categorical — enables > / < comparisons
from pandas import CategoricalDtype
size_type = CategoricalDtype(['S', 'M', 'L', 'XL'], ordered=True)
df.astype({'size': size_type})
```

See [dtypes.md](../dtypes.md) for full `CategoricalDtype` details.

## 4. Rename labels — `.rename()`

### Columns of a frame

```python
df.rename(columns={'open_time': 'date', 'quote_vol': 'quote_volume'})
df.rename(columns=str.lower)                        # apply function to all names
df.rename(columns=lambda c: c.replace(' ', '_'))
```

### Naming a Series

`.rename(scalar)` is the inline way to set `s.name` — it returns a renamed copy, so it drops into a chain where `s.name = 'ret'` (a mutating statement) cannot.

```python
s.rename('ret')                     # scalar → renames the SERIES
pd.Series(values, name='ret')       # or at construction

s.rename({'a': 'A'})                # dict/callable → renames the INDEX LABELS
s.rename_axis('symbol')             # names the INDEX itself, not the Series
```

The name is what downstream operations use as the **column label**, so setting it early saves a rename later:

```python
pd.concat([a.rename('p'), b.rename('q')], axis=1)   # → columns ['p', 'q']
df.join(s.rename('ret'))                            # unnamed Series → ValueError
df.assign(ret=s)                                    # assign supplies the name itself
```

!!! warning "One method, three targets"
    On a Series, `.rename()` switches behaviour on the **argument type**: a scalar sets the Series name, a dict or callable rewrites index labels. On a DataFrame it never touches a name — it only rewrites labels, and needs `index=`/`columns=` to say which axis. `rename_axis` is the separate verb for naming an axis.

## 5. Select or drop columns

```python
df.drop(columns=['ignore', 'close_time'])
df.filter(items=['open', 'high', 'low', 'close'])   # select by name
df.filter(like='taker')                             # names containing 'taker'
df.filter(regex=r'^vol')                            # names matching regex
```

Prefer `.filter()` over `df[['a','b']]` in a chain — keeps the fluent style.

## 6. Sort — `.sort_values()`

```python
df.sort_values('date')
df.sort_values('volume', ascending=False)
df.sort_values(['date', 'symbol'])
```

## 7. Handle missing — `.dropna()` / `.fillna()`

```python
df.dropna(subset=['open', 'close'])     # drop rows where these cols are null
df.fillna({'volume': 0})
df.ffill()                              # forward-fill (time-series gaps)
```

`.dropna()` usually follows `.assign()` calls that produce NaN (e.g. `.pct_change()`).

## 8. String operations — `.assign()` + `.str`

```python
df.assign(
    symbol=lambda d: d['symbol'].str.upper(),
    name=lambda d: d['name'].str.strip().str.lower(),
    base=lambda d: d['symbol'].str[:-4],    # 'BTCUSDT' → 'BTC'
)
```

Chain `.str` methods: `.str.strip().str.lower().str.replace('-', '_')`. Always vectorised — no `.apply()` loop needed.

## 9. Index management — `.set_index()` / `.reset_index()`

```python
df.set_index('date')            # promote column to index (enables resample)
df.set_index('symbol', append=True)  # add a level instead of replacing the index
df.reset_index(drop=True)       # clean 0…n-1 index after filtering/sorting
df.reset_index()                # move index back to a column
df.reset_index(level='symbol')  # move one MultiIndex level back to a column
```

See [multiindex.md](../multiindex.md) for adding, reordering, and flattening index levels.

## 10. Groupby aggregation — `.groupby().agg()`

```python
(df
 .groupby('symbol')
 .agg(
     avg_close=('close', 'mean'),
     total_volume=('volume', 'sum'),
     n=('close', 'count'),
 )
 .sort_values('total_volume', ascending=False)
 .reset_index()
)
```

Named aggregations (`output=('source', 'func')`) name columns directly. The result of `.agg()` re-enters the chain as a normal DataFrame. See [groupby.md](groupby.md) for the full split-apply-combine model (`transform`, `filter`, `apply`).

## 11. Reorder columns

```python
df[['date', 'symbol', 'close', 'open']]          # explicit order; omitted cols are dropped
df.reindex(columns=['date', 'symbol', 'close'])  # like above, but unknown names → all-NaN col
df[df.columns[::-1]]                             # reverse
df.sort_index(axis=1)                            # sort column labels alphabetically
```

Move one column to the front (keep the rest in place):

```python
df[['close'] + [c for c in df.columns if c != 'close']]
df.insert(0, 'close', df.pop('close'))           # in-place: pop then reinsert at position 0
```

- Selection (`df[[...]]`) reorders by **listing columns in the wanted order** — a subset that omits names also drops them.
- `.reindex(columns=...)` is the same reorder but tolerates missing names (adds an all-`NaN` column) — safer when the set is dynamic.
- `.insert(loc, name, values)` and `.pop(name)` mutate in place; the `pop`+`insert` combo relocates a single column to position `loc`.

## 12. Series → DataFrame — `.to_frame()`

A one-column DataFrame needs a **column name**; a Series carries that name in `.name`. `.to_frame(name)` supplies it inline, which is what keeps a chain going after any step that collapses to a Series (`.sum()`, `.value_counts()`, a single-column select).

```python
s.to_frame('ret')                # column named 'ret' — the inline form
s.to_frame()                     # uses s.name; unnamed Series → column 0
s.rename('ret').to_frame()       # same result; sets .name first
pd.DataFrame({'ret': s})         # equivalent, less chain-friendly

(df.groupby('symbol')['ret'].mean()
   .to_frame('avg_ret')
   .reset_index())
```

Keeping the index as a column instead of an index:

```python
s.reset_index(name='ret')                       # index → column, values → 'ret'
s.rename_axis('symbol').reset_index(name='ret')  # name the index column too
```

- `to_frame` returns a new object — it does **not** set `.name` on the original Series.
- `s.rename('x')` sets the name that `to_frame()` then uses as the column label — see [naming a Series](#naming-a-series) for the scalar-vs-dict split.
- `reset_index(name=)` is Series-only, and the index column is called `index` unless the index is named — hence `rename_axis` first.
- `.to_frame().T` gives a one-**row** frame instead (the Series name becomes the row label).
- Several Series at once: `pd.concat([a, b], axis=1, keys=['a', 'b'])` aligns on the index and names the columns in one call.

## Full pipeline example

```python
result = (
    raw
    .query('volume > 0 and close > 0')
    .astype({'open': 'float32', 'high': 'float32',
             'low': 'float32', 'close': 'float32'})
    .assign(
        returns=lambda d: d['close'].pct_change(),
        buy_ratio=lambda d: d['taker_buy_vol'] / d['volume'],
        symbol=lambda d: d['symbol'].str.upper(),
    )
    .rename(columns={'quote_vol': 'quote_volume'})
    .drop(columns=['ignore'])
    .dropna(subset=['returns'])
    .sort_values('date')
    .reset_index(drop=True)
)
```
