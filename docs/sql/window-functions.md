---
tags:
  - performance
---

# Window functions & CTEs

A **window function** computes a value across a set of rows related to the
current row *without* collapsing them — unlike `GROUP BY`, which reduces N
rows to 1 per group. If you think in [pandas](../data/pandas/chaining.md),
window functions are `groupby` + an ordered, row-wise op (`shift`, `rank`,
`rolling`, `cumsum`, ...) broadcast back onto every row instead of
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

## Frame clauses

```sql
ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW   -- running/expanding
ROWS BETWEEN 2 PRECEDING AND CURRENT ROW           -- rolling window of 3
ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING  -- whole partition
```

`ROWS` counts physical rows; `RANGE` groups by the *value* of the `ORDER BY`
column instead (relevant with ties or date ranges) — `ROWS` is what
corresponds to `.rolling(n)`.

## Common Table Expressions (CTEs)

See [basics.md](basics.md) for a first introduction to `WITH`/CTEs outside
the window-function context — this section assumes that and focuses on
multi-stage time-series pipelines.

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

A `WITH name AS (...)` clause is a named, temporary result scoped to the
query that follows. Mechanically it's sugar over a subquery, but it reads
top-to-bottom like a pipeline instead of inside-out — the same reason
[method chaining](../data/pandas/chaining.md) is preferred over deeply
nested calls: each stage is named, single-purpose, and independently
inspectable (`SELECT * FROM returns` to debug one stage).

CTEs aren't automatically materialized — a CTE referenced multiple times
may be re-evaluated each time (some engines materialize automatically or
support `MATERIALIZED` explicitly). `WITH RECURSIVE` is a separate feature
for hierarchical/graph traversal, not covered here.

## Time-series patterns

```sql
-- rolling return
SELECT symbol, t, close / LAG(close) OVER (PARTITION BY symbol ORDER BY t) - 1 AS ret
FROM prices;

-- running drawdown: current value vs. running peak
WITH peak AS (
    SELECT symbol, t, close,
           MAX(close) OVER (PARTITION BY symbol ORDER BY t
                             ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_peak
    FROM prices
)
SELECT symbol, t, close / running_peak - 1 AS drawdown
FROM peak;
```

Same computations as `.groupby('symbol')['close'].pct_change()` and
`.cummax()` in pandas — declarative vs. imperative expression of the same
math. `NULLIF(x, 0)` guards a divide-by-zero (e.g. a Sharpe-like ratio
where the trailing stdev is zero) — SQL has no `NaN` propagation, so an
unguarded division raises instead of silently producing `NaN`.
