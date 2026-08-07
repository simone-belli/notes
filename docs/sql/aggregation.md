# Aggregation: multi-key GROUP BY, HAVING, COUNT(DISTINCT), pivots

Past the [basics](basics.md): `GROUP BY` partitions the post-`WHERE` rows into
groups (one per distinct key), and each aggregate is computed **once per group**,
yielding **exactly one output row per group**. Every rule below follows from that
contract.

## Multi-key GROUP BY

Group by a tuple of columns — one row per distinct *combination* that occurs.

```sql
SELECT   region, product_category, SUM(amount) AS revenue
FROM     sales
GROUP BY region, product_category;
```

- Adding a key makes groups **finer** (more, smaller); removing one makes them
  **coarser**. This is the granularity dial.
- Column order in `GROUP BY` doesn't change which groups exist or the aggregates
  — `GROUP BY a, b` ≡ `GROUP BY b, a`.
- Every non-aggregated `SELECT` column must be in `GROUP BY`.
- Only combinations present in the data are emitted (no zero rows for absent
  pairs). `ROLLUP` / `CUBE` / `GROUPING SETS` add subtotal and grand-total rows
  (not in SQLite).

pandas: `df.groupby(['region', 'product_category'])['amount'].sum()` — the result
`MultiIndex` mirrors the "one row per tuple."

## HAVING vs WHERE

Both filter, but on different things at different times:

| | `WHERE` | `HAVING` |
|---|---|---|
| Filters | individual **rows** | whole **groups** |
| Runs | *before* `GROUP BY` | *after* aggregation |
| Sees aggregates? | **No** (`WHERE SUM(x)>10` errors) | **Yes** |

```sql
SELECT   customer_id, SUM(amount) AS total
FROM     orders
WHERE    status = 'completed'   -- (a) drop rows BEFORE summing
GROUP BY customer_id
HAVING   SUM(amount) > 1000;    -- (b) drop small-total GROUPS after
```

!!! warning "Put it in the right clause"
    Use `WHERE` if the predicate can be decided from a **single raw row**
    (`status = 'completed'`, `order_date >= '2024-01-01'`); use `HAVING` only if
    it needs a **group aggregate** (`SUM(amount) > 1000`, `COUNT(*) >= 3`). A row
    condition in `HAVING` is slower (it aggregates rows it then discards, and
    can't use an index) and often wrong (it filters *after* the sum, so
    `SUM(amount)` already included the rows you meant to exclude). If both kinds
    apply, use both clauses.

`HAVING` without `GROUP BY` treats the whole table as one group. `WHERE` can
never reference a `SELECT` alias (it runs first); repeating the aggregate in
`HAVING` is the portable form.

pandas: `WHERE` ~ a mask before `.groupby()`; `HAVING` ~ `.query(...)` on the
aggregated frame after (or `.groupby(...).filter(...)`).

## COUNT: rows vs values

- `COUNT(*)` — **rows** in the group (includes `NULL`s).
- `COUNT(col)` — rows where `col` **is not NULL**.
- `COUNT(DISTINCT col)` — **distinct non-NULL values** of `col`.

```sql
SELECT   region,
         COUNT(*)                    AS orders,        -- rows
         COUNT(DISTINCT customer_id) AS unique_buyers  -- distinct entities
FROM     orders
GROUP BY region;
```

- `NULL` is never counted by `COUNT(DISTINCT)`.
- It's **more expensive** than a plain count — the engine must de-duplicate
  (hash/sort) per group. Warehouses offer `APPROX_COUNT_DISTINCT` (HyperLogLog)
  as a cheap estimate.
- Multi-column distinct varies: `COUNT(DISTINCT a, b)` (MySQL),
  `COUNT(DISTINCT (a, b))` (Postgres); SQLite is single-column only. `DISTINCT`
  also works in `SUM`/`AVG`.

!!! note "Two different DISTINCTs"
    `SELECT DISTINCT` de-duplicates whole output rows (after `SELECT`);
    `COUNT(DISTINCT col)` de-duplicates values inside one aggregate. Same word,
    different mechanism.

pandas: `COUNT(*)` ~ `.size()`; `COUNT(col)` ~ `.count()`;
`COUNT(DISTINCT col)` ~ `.nunique()`.

## Conditional aggregation — the pivot idiom

Put a `CASE` **inside** an aggregate so it only sums/counts matching rows. One
column per category = rows pivoted into columns, by hand.

```sql
SELECT
    region,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed,
    SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled,
    SUM(CASE WHEN status = 'completed' THEN amount ELSE 0 END) AS revenue
FROM     orders
GROUP BY region;
```

`SUM(CASE WHEN cond THEN 1 ELSE 0 END)` counts matching rows; swap `1` for a
column to sum a subset. This is the portable pivot in engines with no `PIVOT`
keyword (Postgres, SQLite, MySQL).

- **`COUNT` variant** — `COUNT(CASE WHEN cond THEN 1 END)`: `COUNT` skips the
  `NULL` from the missing `ELSE`, so no `ELSE 0` needed. (The `THEN` value must
  be non-NULL; the else branch must stay `NULL`.)
- **Rate** — `AVG(CASE WHEN cond THEN 1.0 ELSE 0 END)` is the **fraction**
  matching (mean of 1s and 0s). Use `1.0` to avoid integer division.
- **`FILTER`** — Postgres' `COUNT(*) FILTER (WHERE cond)` /
  `SUM(x) FILTER (WHERE cond)` is the readable standard-SQL spelling (not in
  MySQL/SQLite).

!!! tip "One scan, many slices"
    Conditional aggregation computes many slices — completed vs cancelled,
    this-year vs last-year — as separate columns in **one pass**, instead of N
    queries or N self-joins.

pandas: this is `pd.crosstab` / `pd.pivot_table` /
`df.groupby(...).value_counts().unstack()`.

## All four together

```sql
SELECT   region, product_category,
         COUNT(DISTINCT customer_id) AS buyers,
         SUM(CASE WHEN status = 'completed' THEN amount ELSE 0 END) AS revenue,
         AVG(CASE WHEN status = 'cancelled' THEN 1.0 ELSE 0 END)    AS cancel_rate
FROM     orders
WHERE    order_date >= '2024-01-01'          -- row filter, pre-grouping
GROUP BY region, product_category            -- multi-key
HAVING   COUNT(DISTINCT customer_id) >= 5;   -- group filter, post-aggregation
```
