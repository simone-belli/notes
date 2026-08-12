---
tags:
  - performance
---

# Window functions & CTEs

A **window function** computes a value across a set of rows related to the
current row *without* collapsing them — unlike `GROUP BY`, which reduces N
rows to 1 per group. If you think in pandas, window functions are
[`groupby` + an ordered, row-wise op](../data/pandas/windows.md) (`shift`,
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

## Top-N per group

"Top 3 highest-paid employees per department", "most recent order per customer",
"2 largest trades per symbol" — all the same shape, and a classic interview
question. A window function **can't** go in `WHERE` (it's computed *after* `WHERE`
in the [logical order](aggregation.md)), so number the rows in a
[CTE](subqueries.md) and filter in the outer query:

```sql
WITH ranked AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY department
                              ORDER BY salary DESC) AS rn
    FROM employees
)
SELECT department, name, salary
FROM ranked
WHERE rn <= 3;            -- rn = 1 for the single top row per group
```

`ROW_NUMBER()` numbers each group `1, 2, 3, …` in descending salary; `rn <= n`
slices the top `n` of every group in one pass — replacing a clumsy correlated
subquery.

!!! warning "Which ranking function you filter on changes the meaning of \"top N\""
    At a tie on the boundary: **`ROW_NUMBER` + `rn <= 3`** → exactly 3 rows,
    ties cut arbitrarily. **`RANK` + `rk <= 3`** → keeps ranks `1,2,2` (can be
    ≥3 rows), all tied rows qualify. **`DENSE_RANK` + `dr <= 3`** → every row in
    the top 3 distinct *values* (e.g. "top 3 salary bands"). "Top 3" is ambiguous
    exactly at ties — say which you mean.

**Deduplication** is the top-1 special case: `ROW_NUMBER() ... = 1`, partitioned
by the key that defines a duplicate, ordered by recency/priority, keeps the best
row per key.

```sql
WITH d AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY email ORDER BY updated_at DESC) AS rn
    FROM contacts
)
SELECT * FROM d WHERE rn = 1;    -- newest row per email
```

Same as `df.sort_values('updated_at').groupby('email').tail(1)`.

## Gaps and islands

Detecting **consecutive runs** in ordered data — a login streak, a period a
sensor stayed "on", contiguous ID ranges — and collapsing each run to
`(start, end, length)`. **Islands** are the runs; **gaps** are the holes
between them. It's the canonical hard window-function interview question, and
structurally a **streak / regime detector**: the imperative "loop and keep a
counter, reset on change" becomes the set-based "manufacture a key that's
constant within each run, then `GROUP BY` it".

!!! note "The core trick: two counters that drift apart"
    Two monotonic sequences that both step by 1 stay a **constant distance
    apart** — until the data skips. Subtract them and the difference is
    constant within a run and jumps between runs, so it works as a group key.

**Consecutive values** (dense dates/integers): the data itself is one counter,
`ROW_NUMBER()` is the other. Within a run of consecutive days both climb by 1,
so `date − rn` is constant per run:

```sql
WITH numbered AS (
    SELECT user_id, login_date,
           login_date - INTERVAL (ROW_NUMBER() OVER (PARTITION BY user_id
                                  ORDER BY login_date)) DAY AS grp   -- anchor date, constant per run
    FROM logins
)
SELECT user_id, MIN(login_date) AS start_date, MAX(login_date) AS end_date, COUNT(*) AS len
FROM numbered
GROUP BY user_id, grp;
```

**Same-value runs** (the general `ROW_NUMBER()` *difference*): number rows
twice — once over the whole partition, once partitioned by the value tracked —
and subtract. `rn_all − rn_grp` is constant along each maximal same-value run:

```sql
WITH numbered AS (
    SELECT machine_id, t, status,
           ROW_NUMBER() OVER (PARTITION BY machine_id ORDER BY t)         AS rn_all,
           ROW_NUMBER() OVER (PARTITION BY machine_id, status ORDER BY t) AS rn_grp
    FROM status_log
)
SELECT machine_id, status, MIN(t) AS run_start, MAX(t) AS run_end, COUNT(*) AS len
FROM numbered
GROUP BY machine_id, status, rn_all - rn_grp;   -- value + diff: the pair is unique per run
```

!!! warning "Group by the value *and* the difference"
    `rn_all − rn_grp` can repeat across two runs of the **same** value, so
    grouping on the bare difference merges them. Always `GROUP BY` the value
    column **together with** the difference — the pair is unique per run.

**Boundary-flag + cumulative sum** — the more flexible idiom: flag where a run
starts with [`LAG`](#mapping-to-pandas), then a running `SUM` of the flags is
the run id. Unlike the `ROW_NUMBER` difference, the boundary rule is arbitrary
(value change, or a time gap over a threshold for sessionising):

```sql
WITH flagged AS (
    SELECT *, CASE WHEN status = LAG(status) OVER (PARTITION BY machine_id ORDER BY t)
                   THEN 0 ELSE 1 END AS is_new_run
    FROM status_log
)
SELECT machine_id, status, MIN(t), MAX(t), COUNT(*)
FROM (SELECT *, SUM(is_new_run) OVER (PARTITION BY machine_id ORDER BY t) AS run_id FROM flagged) g
GROUP BY machine_id, run_id, status;
```

This is exactly the pandas `(s != s.shift()).cumsum()` group-key idiom. To
report the **gaps** instead, pair each row with the next via `LEAD` and keep
the jumps: `WHERE LEAD(id) OVER (ORDER BY id) - id > 1`.

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
