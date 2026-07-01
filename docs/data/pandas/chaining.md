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

---

## Common chain operations — catalog

| # | Method | What it does |
|---|--------|-------------|
| 1 | `.query(expr)` | Filter rows |
| 2 | `.assign(**kwargs)` | Add or transform columns |
| 3 | `.astype(dict)` | Cast dtypes |
| 4 | `.rename(columns=...)` | Rename columns |
| 5 | `.drop(columns=[...])` / `.filter(...)` | Remove or select columns |
| 6 | `.sort_values(by=...)` | Sort rows |
| 7 | `.dropna()` / `.fillna(...)` | Handle missing values |
| 8 | `.assign(c=lambda d: d['c'].str...)` | String operations on a column |
| 9 | `.set_index()` / `.reset_index(drop=True)` | Index management |
| 10 | `.groupby().agg(...)` | Aggregate by group |

### 1. Filter rows — `.query()`

```python
df.query('price > 0 and volume > 1_000')
df.query('status == "active"')
df.query('date > @cutoff')      # @ = Python variable
```

!!! tip "assign() lambdas see columns added earlier in the same call"
    Within one `.assign()` call, `lambda d: ...` receives the DataFrame as it exists at that point — including columns defined by earlier keyword arguments in the same call. This lets you build derived columns in sequence without chaining multiple `.assign()` calls.

### 2. Add / transform columns — `.assign()`

See the section above. Key: lambdas see columns added earlier in the same call.

### 3. Cast dtype — `.astype()`

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

See [dtypes.md](dtypes.md) for full `CategoricalDtype` details.

### 4. Rename columns — `.rename()`

```python
df.rename(columns={'open_time': 'date', 'quote_vol': 'quote_volume'})
df.rename(columns=str.lower)                        # apply function to all names
df.rename(columns=lambda c: c.replace(' ', '_'))
```

### 5. Select or drop columns

```python
df.drop(columns=['ignore', 'close_time'])
df.filter(items=['open', 'high', 'low', 'close'])   # select by name
df.filter(like='taker')                             # names containing 'taker'
df.filter(regex=r'^vol')                            # names matching regex
```

Prefer `.filter()` over `df[['a','b']]` in a chain — keeps the fluent style.

### 6. Sort — `.sort_values()`

```python
df.sort_values('date')
df.sort_values('volume', ascending=False)
df.sort_values(['date', 'symbol'])
```

### 7. Handle missing — `.dropna()` / `.fillna()`

```python
df.dropna(subset=['open', 'close'])     # drop rows where these cols are null
df.fillna({'volume': 0})
df.ffill()                              # forward-fill (time-series gaps)
```

`.dropna()` usually follows `.assign()` calls that produce NaN (e.g. `.pct_change()`).

### 8. String operations — `.assign()` + `.str`

```python
df.assign(
    symbol=lambda d: d['symbol'].str.upper(),
    name=lambda d: d['name'].str.strip().str.lower(),
    base=lambda d: d['symbol'].str[:-4],    # 'BTCUSDT' → 'BTC'
)
```

Chain `.str` methods: `.str.strip().str.lower().str.replace('-', '_')`. Always vectorised — no `.apply()` loop needed.

### 9. Index management — `.set_index()` / `.reset_index()`

```python
df.set_index('date')            # promote column to index (enables resample)
df.reset_index(drop=True)       # clean 0…n-1 index after filtering/sorting
df.reset_index()                # move index back to a column
```

### 10. Groupby aggregation — `.groupby().agg()`

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

Named aggregations (`output=('source', 'func')`) name columns directly. The result of `.agg()` re-enters the chain as a normal DataFrame.

### Full pipeline example

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
