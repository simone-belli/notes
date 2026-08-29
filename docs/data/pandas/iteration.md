---
tags:
  - performance
quiz: detail
---

# Pandas — Iteration

## `__iter__` asymmetry

`Series.__iter__` yields **values**; `DataFrame.__iter__` yields **column labels** — not rows.

```python
for v in series:     # values: 10, 20, 30
for col in df:       # column names: 'x', 'y'
```

## Series

| Method | Yields |
|--------|--------|
| `for v in s` | values |
| `s.items()` | `(label, value)` pairs |

```python
for label, value in s.items():
    print(label, value)
```

## DataFrame — column iteration

```python
for col_name, col_series in df.items():   # (str, Series) per column
    print(col_name, col_series.dtype)
```

## DataFrame — row iteration

| Method | Yields | Notes |
|--------|--------|-------|
| `iterrows()` | `(index, Series)` per row | Slow; coerces all dtypes to common type |
| `itertuples()` | `namedtuple` per row | Faster; preserves column dtypes |

```python
for idx, row in df.iterrows():
    print(row['x'])          # Series access — dtype may be coerced

for row in df.itertuples(index=True, name='Row'):
    print(row.x, row.y)      # attribute access — dtypes preserved
```

!!! warning "iterrows coerces dtypes"
    Because a row `Series` must have a single dtype, mixed-dtype rows get cast to `object`. `itertuples` avoids this — each field carries its original column dtype.

## Scalar access in loops

Prefer `.at`/`.iat` over `.loc`/`.iloc` when accessing a single cell repeatedly:

```python
df.at[idx, 'col']    # label — skips Series overhead
df.iat[i, j]         # position
```

## Performance hierarchy

```
vectorized ops  >  np.where  >  apply(axis=1)  >  itertuples  >  iterrows
```

Reach for a vectorized expression first. Use `itertuples` when a Python loop is unavoidable; avoid `iterrows` unless dtype coercion is acceptable. For `apply` itself — `axis` semantics and when a plain `f(df)` beats it — see [Apply](transforming/apply.md).

To materialise the whole frame as Python structures at once (rather than loop), see [to_dict()](to-dict.md).
