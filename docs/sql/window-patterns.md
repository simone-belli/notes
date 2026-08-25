---
tags:
  - performance
---

# Window Patterns

Query shapes built on [window functions](window-functions.md) that come up
again and again: ranking within a group, collapsing runs of consecutive
rows, and the time-series recipes both feed.

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

## Related

- [Window functions](window-functions.md) — `OVER`/`PARTITION BY`/frame mechanics and the pandas mapping
- [Subqueries & CTEs](subqueries.md) — the `WITH` staging these patterns lean on
- [Aggregation](aggregation.md) — `GROUP BY`, `HAVING`, and conditional aggregation
