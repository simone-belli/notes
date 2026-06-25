# Method Chaining and SettingWithCopyWarning

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

## SettingWithCopyWarning

Triggered by **chained indexing used for assignment**: two `[]` operations where the first may return a copy.

```python
df[df['age'] > 18]['name'] = 'adult'   # WARNING — assignment likely lost
```

Step 1 (`df[df['age'] > 18]`) returns a new object (view or copy — not guaranteed). Step 2 writes to that object. If it's a copy, `df` is unchanged.

**Why view vs copy is unpredictable:** NumPy returns a view for contiguous slices, a copy for boolean masks and fancy integer indexing. Pandas can't tell you which you got.

### The fix: `.loc` for any write

`.loc[row_mask, col]` is a single operation directly on the original — no intermediate object.

```python
df.loc[df['age'] > 18, 'name'] = 'adult'   # correct
```

**Rule: reading can chain; writing must use `.loc` on the original.**

### Explicit `.copy()` for an independent subset

```python
subset = df[df['age'] > 18].copy()   # explicit intent: separate object
subset['name'] = 'adult'             # safe, no warning
```

### Decision table

| Intent | Pattern | Correct? |
|--------|---------|----------|
| Read from subset | `df[mask]['col'].mean()` | Yes |
| Modify original | `df.loc[mask, 'col'] = v` | Yes |
| Work with a separate copy | `sub = df[mask].copy(); sub['col'] = v` | Yes |
| Modify original (wrong way) | `df[mask]['col'] = v` | No — warning |

### Pandas 2.0+ Copy-on-Write (CoW)

CoW (default in pandas 3.0) makes every indexing result a copy — view-mutation is gone, the warning disappears. Code that wrote to a slice expecting to modify the original silently breaks. Fix: `.loc` on the original, which is correct under both old and CoW semantics.
