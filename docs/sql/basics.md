# SQL basics: SELECT, JOIN, GROUP BY, subqueries, CTEs

Structural Query Language (SQL) is **declarative** — you describe the result
you want, not how to compute it. The engine's query planner picks the actual
execution strategy.

## Query anatomy

```sql
SELECT column_a, column_b
FROM   my_table
WHERE  column_a > 100
ORDER BY column_b DESC
LIMIT  10;
```

!!! note "Logical processing order"
    Clauses are *written* `SELECT → FROM → WHERE → ORDER BY → LIMIT` but
    *executed* `FROM/JOIN → WHERE → GROUP BY → HAVING → SELECT → ORDER BY →
    LIMIT`. This is why a `SELECT`-defined alias can't be used in `WHERE`
    (`WHERE` runs first) but can be used in `ORDER BY` (runs after `SELECT`).

- `WHERE` filters rows; can't reference aggregates (`WHERE SUM(x) > 10` is
  invalid — use `HAVING`, see below).
- `LIMIT` (+ optional `OFFSET`) truncates the sorted result. Without
  `ORDER BY`, `LIMIT` is nondeterministic — always pair the two.
- `NULL = NULL` is `UNKNOWN`, not `TRUE` — use `IS NULL` / `IS NOT NULL`,
  never `= NULL`.

## JOINs

- **`INNER JOIN`** — only rows matching the join key on both sides;
  non-matches dropped entirely.
- **`LEFT JOIN`** — all rows from the left table; unmatched right-side
  columns come back `NULL`.
- **Anti-join** — "rows in A with no match in B." No dedicated keyword: a
  `LEFT JOIN` filtered to where the right key is `NULL`.

```sql
SELECT c.name, o.order_id
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id;

-- anti-join: customers who have never ordered
SELECT c.name
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.customer_id
WHERE o.customer_id IS NULL;      -- keep only the unmatched left rows
```

Filter on the join key (or another right column that's non-`NULL` whenever a
match exists) — a nullable data column could be `NULL` on a *matched* row. The
anti-join is equivalent to [`NOT EXISTS`](#subqueries); use the `LEFT JOIN` form
when you also want columns, `NOT EXISTS` for a plain yes/no.

`INNER JOIN` ~ `df.merge(other, how='inner')`; `LEFT JOIN` ~
`df.merge(other, how='left')`; the `ON` key is pandas' `on=`.

!!! warning "The fan-out trap"
    Joining `orders` (one row per order) to `order_items` (many rows per
    order) turns 1 order row into N item rows — the join is correct, but a
    `SUM(amount)` computed *after* the join double-counts `amount` for
    every extra item row. **Detect** it by comparing row counts across the
    join: if `COUNT(*)` after the join exceeds the left table's, the
    many-side fanned out and any post-join `SUM`/`COUNT`/`AVG` is inflated.
    **Fix** it by aggregating the many-side down to one row per key *before*
    joining, not after. This is the same trap as a one-to-many
    `df.merge()` inflating a `.groupby().sum()` run afterward in pandas
    (where `merge(..., validate='one_to_many')` catches it) — check
    join-key cardinality before trusting a post-join aggregate.

## GROUP BY, WHERE vs HAVING

```sql
SELECT customer_id, SUM(amount) AS total_spent
FROM orders
WHERE order_date >= '2024-01-01'   -- filters ROWS, before grouping
GROUP BY customer_id
HAVING SUM(amount) > 1000;         -- filters GROUPS, after aggregation
```

Any non-aggregated `SELECT` column must appear in `GROUP BY`. Filter with
`WHERE` whenever possible (cheaper, runs before grouping); reserve `HAVING`
for conditions that genuinely need the aggregate result.

pandas: `WHERE` ~ a boolean mask before `.groupby()`; `HAVING` ~
`.groupby(...).sum().query(...)` after.

## Subqueries

- **Uncorrelated** (derived table) — self-contained, computed once.
  ```sql
  SELECT name FROM employees
  WHERE salary > (SELECT AVG(salary) FROM employees);
  ```
- **Correlated** — references a column from the outer query, conceptually
  re-evaluated per outer row. Typical form: `IN` vs `EXISTS`.
  ```sql
  SELECT name FROM employees e
  WHERE EXISTS (
      SELECT 1 FROM departments d
      WHERE d.dept_id = e.dept_id AND d.city = 'NYC'
  );
  ```

!!! warning "NOT IN + NULL"
    If the subquery behind `NOT IN` returns even one `NULL`, the whole
    `NOT IN` predicate matches nothing (three-valued logic). `NOT EXISTS`
    doesn't have this trap — prefer it for "no counterpart in B" checks.

## A first CTE

```sql
WITH high_spenders AS (
    SELECT customer_id, SUM(amount) AS total_spent
    FROM orders
    GROUP BY customer_id
    HAVING SUM(amount) > 1000
)
SELECT c.name, h.total_spent
FROM high_spenders h
JOIN customers c ON c.customer_id = h.customer_id;
```

`WITH name AS (...)` is sugar over a subquery, but named, composable, and
independently testable (`SELECT * FROM high_spenders` to debug one stage) —
the same instinct as chaining [`.assign()`/`.pipe()`](../data/pandas/chaining.md)
over deeply nested pandas calls. See [window functions](window-functions.md)
for CTEs used in multi-stage time-series pipelines.
