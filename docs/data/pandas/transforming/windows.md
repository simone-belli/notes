# Pandas — Window Operations

`shift`, `rolling`, and `expanding` are pandas' **window operations**: they compute a value for each row from a set of neighbouring rows **without collapsing** them (N rows in, N rows out) — unlike [`groupby().agg()`](groupby.md), which reduces each group to one row. They are SQL window functions (`OVER (PARTITION BY … ORDER BY …)`) expressed as method calls; see [SQL window functions](../../../sql/window-functions.md) for the declarative side.

The three parts of an `OVER` clause map directly:

- **`PARTITION BY g`** → `df.groupby('g')` (window resets per group).
- **`ORDER BY t`** → the row order (you must `sort_values('t')` first — there is no `ORDER BY` inside the window).
- **frame clause** → which method: `shift` / `rolling` / `expanding`.

## `shift` — LAG / LEAD

`shift(k)` moves values down `k` rows (exposing the predecessor); `shift(-k)` moves up (the successor). Edge cells become `NaN`.

```python
df['prev'] = df.groupby('symbol')['close'].shift(1)    # LAG(close)
df['next'] = df.groupby('symbol')['close'].shift(-1)   # LEAD(close)
```

- `diff(k)` = `x - x.shift(k)` (step change); `pct_change(k)` = `x / x.shift(k) - 1` (fractional return).

!!! warning "Always `groupby` first"
    `df['close'].shift(1)` leaks the last row of one symbol into the first row of the next — the SQL bug of omitting `PARTITION BY`. Grouping makes the first row of each group correctly `NaN` (a partition boundary).

## `rolling(n)` — fixed trailing window

`rolling(n)` slides a window of the **n most recent rows** (current + `n-1` before) and reduces each.

```python
df['ma20'] = (df.groupby('symbol')['close']
                .rolling(20).mean()
                .reset_index(level=0, drop=True))
```

- **`min_periods`** — non-NaN observations needed before emitting a value (default = window size → first `n-1` rows are `NaN`); `min_periods=1` emits partial windows immediately.
- **`center=True`** — centre on the current row (uses future rows — not causal).
- **`.rolling(n).agg([...])`** / **`.apply(f, raw=True)`** — multiple reducers, or an arbitrary window→scalar function.
- **`rolling('7D')`** on a `DatetimeIndex` — all rows within the trailing 7 *days* (SQL's value-based `RANGE` frame), not a row count. Right for irregular timestamps.

!!! warning "Off-by-one vs SQL"
    `rolling(n)` counts **total window size**. SQL counts rows *preceding*, so `ROWS BETWEEN 19 PRECEDING AND CURRENT ROW` (20 rows) is `rolling(20)`. Rule: `rolling(n)` ↔ `n-1 PRECEDING`.

## `expanding()` — anchored, unbounded frame

A window that starts at the first row and **grows to include the current row** — every row sees all history up to itself (`ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`).

```python
df['peak'] = df.groupby('symbol')['close'].expanding().max()      # running peak
df['dd']   = df['close'] / df.groupby('symbol')['close'].cummax() - 1   # drawdown
```

Cumulative methods are fast named shortcuts for the common cases:

| Expanding form | Shortcut | SQL |
|----------------|----------|-----|
| `expanding().sum()` | `cumsum()` | `SUM(x) OVER (ORDER BY t)` |
| `expanding().max()` | `cummax()` | `MAX(x) OVER (ORDER BY t …)` |
| `expanding().min()` | `cummin()` | `MIN(x) OVER (…)` |
| — | `cumcount()` (0-based) | `ROW_NUMBER() - 1` |

## Two reflexes

1. **Sort the rows.** Window ops trust row order; `sort_values(['symbol', 't'])` first or the neighbours are meaningless. (`groupby(sort=True)` sorts group *keys*, not rows within a group.)
2. **`groupby` to partition** so the window resets at each group edge — otherwise one group's values bleed into the next.

!!! note "`groupby().rolling()` returns a MultiIndex"
    It yields a Series indexed by `(group, original_index)`. Realign it with `.reset_index(level=0, drop=True)`, or use `groupby('g')['x'].transform(lambda s: s.rolling(n).mean())`. `shift`/`diff`/`pct_change`/`cumsum` already return same-index output — assign straight back.
