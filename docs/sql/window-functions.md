---
tags:
  - performance
---

# Window Functions

A **window function** computes a value across a set of rows related to the
current row *without* collapsing them — unlike `GROUP BY`, which reduces N
rows to 1 per group. If you think in pandas, window functions are
[`groupby` + an ordered, row-wise op](../data/pandas/transforming/windows.md) (`shift`,
`rank`, `rolling`, `cumsum`, ...) broadcast back onto every row instead of
aggregated away.

```sql
<function>(<args>) OVER (
    [PARTITION BY <columns>]   -- like groupby(cols)
    [ORDER BY <columns>]       -- like sort_values within each group
    [<frame clause>]           -- like .rolling(n) / .expanding()
)
```

!!! note "Mental model"
    `OVER (PARTITION BY g ORDER BY t)` is `df.sort_values('t').groupby('g')`
    — except every row survives in the output instead of collapsing to one
    row per group. Window functions = "groupby that doesn't collapse."

## Mapping to pandas

| SQL | pandas | What it does |
|-----|--------|---------------|
| `LAG(x) OVER (PARTITION BY g ORDER BY t)` | `df.groupby('g')['x'].shift(1)` | Value from 1 row before, within group |
| `LEAD(x) OVER (...)` | `df.groupby('g')['x'].shift(-1)` | Value from 1 row after |
| `ROW_NUMBER() OVER (PARTITION BY g ORDER BY t)` | `df.groupby('g').cumcount() + 1` | Sequential rank, no ties |
| `RANK() OVER (PARTITION BY g ORDER BY x)` | `df.groupby('g')['x'].rank(method='min')` | Rank with gaps after ties |
| `DENSE_RANK() OVER (PARTITION BY g ORDER BY x)` | `df.groupby('g')['x'].rank(method='dense')` | Rank, ties share, no gaps |
| `SUM(x) OVER (PARTITION BY g ORDER BY t)` | `df.groupby('g')['x'].cumsum()` | Running total |
| `SUM(x) OVER (... ROWS BETWEEN n PRECEDING AND CURRENT ROW)` | `df.groupby('g')['x'].rolling(n+1).sum()` | Rolling sum |
| `MAX(x) OVER (... ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)` | `df.groupby('g')['x'].cummax()` | Running maximum |

!!! warning "Off-by-one on window size"
    `ROWS BETWEEN n PRECEDING AND CURRENT ROW` spans `n + 1` rows (current
    row plus `n` before it). pandas' `.rolling(n)` treats `n` as the total
    window size — `2 PRECEDING` maps to `.rolling(3)`, not `.rolling(2)`.

`LAG`/`LEAD` produce `NULL` at partition boundaries, like `.shift()`
produces `NaN` at group edges — both need an explicit `PARTITION BY` /
`groupby` or they'll leak values across logical groups.

!!! note "`ROW_NUMBER` vs `RANK` vs `DENSE_RANK` on ties"
    For values ordered `100, 90, 90, 80`: `ROW_NUMBER` → `1, 2, 3, 4`
    (always distinct, ties broken arbitrarily); `RANK` → `1, 2, 2, 4`
    (ties share, then a **gap** — "Olympic" ranking); `DENSE_RANK` →
    `1, 2, 2, 3` (ties share, **no gap**). Pick `ROW_NUMBER` for exactly one
    row per position (dedup, top-1), `RANK`/`DENSE_RANK` when ties should
    legitimately tie. Add tiebreaker columns to `ORDER BY` to make
    `ROW_NUMBER` deterministic.

!!! tip "Rank over the whole table"
    `PARTITION BY` is optional. Omit it — `RANK() OVER (ORDER BY salary DESC)` —
    and the window is the *entire* result set, so the rank is **global** instead
    of per-group (`ORDER BY` is still required; it's what you rank by). Same as
    dropping the `.groupby()`: `df['salary'].rank(method='min', ascending=False)`.

## Frame clauses

The **frame** is the slice of the partition the aggregate sees *for the current
row* — what turns a window aggregate into a *running* / *rolling* quantity rather
than a partition-wide constant.

```sql
ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW   -- running/expanding  → .expanding()
ROWS BETWEEN 2 PRECEDING AND CURRENT ROW           -- rolling window of 3 → .rolling(3)
ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING  -- whole partition
```

### Default frame — what you get when you omit one

- **No `ORDER BY`** → whole partition (`RANGE … UNBOUNDED PRECEDING AND UNBOUNDED
  FOLLOWING`). `SUM(x) OVER (PARTITION BY g)` is the group total on every row (the
  "% of group" move).
- **`ORDER BY`, no frame** → `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`.
  This is what makes `SUM(x) OVER (ORDER BY t)` a *running* total — but the
  default is **`RANGE`, not `ROWS`**.

### `ROWS` vs `RANGE`

`ROWS` counts **physical rows**: `CURRENT ROW` is this one row. `RANGE` counts by
the **value** of the `ORDER BY` column: `CURRENT ROW` means *all rows whose
`ORDER BY` value ties the current one*. With a unique `ORDER BY` key they're
identical; they diverge only on **ties**.

!!! warning "Default `RANGE` + ties = silent bug"
    A "running total" `SUM(amt) OVER (ORDER BY day)` where `day` repeats gives
    **every tied row the same cumulative value** — the default `RANGE` frame
    sweeps all same-`day` peers into `CURRENT ROW` at once. For a true
    row-by-row running total, write the frame explicitly:
    `SUM(amt) OVER (ORDER BY day ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)`.
    Rule: if you mean "up to and including *this* row", say `ROWS`. `ROWS` is also
    what maps to pandas' `.rolling(n)` / `.expanding()`; `RANGE` is for genuine
    value-based windows ("within 7 days").


## Staging a window pipeline with a CTE

Window expressions get unwieldy inline — a derived column that a later
window needs has to be computed in an earlier stage. A Common Table
Expression (CTE) names that stage, and a `WINDOW` clause names a reused
window spec:

```sql
WITH returns AS (
    SELECT symbol, t, close / LAG(close) OVER (PARTITION BY symbol ORDER BY t) - 1 AS ret
    FROM prices
)
SELECT symbol, t, ret,
       AVG(ret) OVER w AS mean_20d
FROM returns
WINDOW w AS (PARTITION BY symbol ORDER BY t ROWS BETWEEN 19 PRECEDING AND CURRENT ROW);
```

CTEs themselves — what `WITH` means, why it beats inside-out nesting, the
materialization caveat, and `WITH RECURSIVE` — are covered in
[Subqueries & CTEs](subqueries.md).

## Applied patterns

Top-N per group, gaps-and-islands, and the time-series recipes built on
these mechanics are on their own page: [Window Patterns](window-patterns.md).

## Related

- [Window Patterns](window-patterns.md) — top-N per group, gaps and islands, time-series recipes
- [Subqueries & CTEs](subqueries.md) — `WITH`, nesting vs pipelines, recursive CTEs
- [Window Operations](../data/pandas/transforming/windows.md) — the pandas side of the same mapping
