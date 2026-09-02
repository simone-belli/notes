# Subqueries & CTEs

Past the [basics](basics.md): a subquery is a `SELECT` nested in another
statement. The axis that matters is **whether the inner query depends on the
outer**:

- **Uncorrelated** — self-contained; conceptually run **once**.
- **Correlated** — references an outer column; conceptually re-run **per outer
  row**.

## Uncorrelated

**Derived table** — a subquery in `FROM` returns a *table*; must be aliased. Use
it to compute an aggregate/window column and then filter or join on it — the fix
for "can't reference an aggregate/window output in the same query's `WHERE`" (see
[aggregation](aggregation.md), logical order).

```sql
SELECT region, avg_order
FROM (SELECT region, AVG(amount) AS avg_order FROM orders GROUP BY region) AS r
WHERE avg_order > 100;          -- alias `r` mandatory
```

**Scalar subquery** — returns exactly one row × one column, usable where a single
value is expected (`SELECT`, `WHERE`). >1 row is a runtime error; 0 rows yields
`NULL`. In `SELECT`, an uncorrelated scalar is a constant broadcast to every row.

```sql
SELECT name, salary FROM employees
WHERE salary > (SELECT AVG(salary) FROM employees);   -- one number
```

## Correlated: EXISTS / IN

```sql
SELECT name FROM employees e
WHERE EXISTS (SELECT 1 FROM departments d          -- correlated: references e
              WHERE d.dept_id = e.dept_id AND d.city = 'NYC');
```

- `EXISTS` — boolean; true at the first matching inner row, then short-circuits.
  The inner `SELECT` list is irrelevant (`SELECT 1`). Almost always correlated.
- `IN` — tests a value against a *column* of values; commonly **uncorrelated**
  (`e.dept_id IN (SELECT dept_id FROM departments WHERE city='NYC')`).

!!! warning "NOT IN + NULL"
    If a `NOT IN` subquery returns even one `NULL`, the predicate is `UNKNOWN`
    for every row and matches **nothing** (three-valued logic). `NOT EXISTS` has
    no such trap — prefer it for "not present in B."

## A correlated subquery is often a JOIN in disguise

A correlated subquery does a keyed lookup into another table per outer row — what
a join does.

- **`EXISTS`/`IN` → semi-join**; **`NOT EXISTS` → anti-join**
  (`LEFT JOIN … WHERE right IS NULL`).
- **Correlated scalar aggregate in `SELECT` → `GROUP BY` + `JOIN`:**

```sql
-- per-row: COUNT runs once per customer (N subqueries)
SELECT c.name,
       (SELECT COUNT(*) FROM orders o WHERE o.customer_id = c.customer_id) AS n
FROM customers c;

-- one grouped pass instead
SELECT c.name, COUNT(o.order_id) AS n
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.customer_id
GROUP BY c.customer_id, c.name;
```

Use `LEFT JOIN` so zero-order customers survive with `COUNT = 0`; `COUNT(col)`
(not `COUNT(*)`) counts the unmatched `NULL` side as 0.

!!! warning "The rewrite can multiply rows"
    `EXISTS` returns each left row **at most once** (semi-join); a plain
    `INNER JOIN` returns **one row per match** — the [fan-out
    trap](basics.md). Rewriting `EXISTS` as a join may need `SELECT DISTINCT` or
    pre-aggregation to restore one-row-per-left-row.

!!! tip "Rule of thumb"
    Prefer the **join** for per-row aggregates (one pass beats N). Keep the
    **subquery** when you want semi-/anti-join semantics (`EXISTS`/`NOT EXISTS`,
    no row multiplication) or when it reads more clearly.

## Deep nesting is what CTEs replace

Chained subqueries nest **inside-out**: the innermost, most-indented `SELECT`
runs first, and each stage is an anonymous, untestable, sometimes-duplicated
block. A **Common Table Expression (CTE)** (`WITH name AS (...)`) names each
stage and lays them **top-to-bottom** as a pipeline.

```sql
WITH per_customer AS (
    SELECT region, customer_id, SUM(amount) AS order_total
    FROM orders WHERE order_date >= '2024-01-01'
    GROUP BY region, customer_id
),
per_region AS (
    SELECT region, AVG(order_total) AS avg_order
    FROM per_customer GROUP BY region
)
SELECT region, avg_order FROM per_region WHERE avg_order > 500;
```

Each stage is named, single-purpose, reads in execution order, is independently
inspectable (`SELECT * FROM per_customer`), and a name reused twice is written
once — the exact instinct behind chaining [`.pipe()`](../pandas/transforming/chaining.md)
calls in pandas rather than nesting them inside-out. Each `WITH stage AS (...)`
maps to one `.pipe(f)`: a named, single-purpose step you can inspect on its own.

!!! note "CTE ≈ named subquery"
    A non-recursive CTE is sugar over a subquery (same semantics) — a
    *readability* tool, not a performance one. Materialization is
    engine-dependent: a CTE used twice may be **recomputed** each time (some
    engines materialize automatically or take `MATERIALIZED` / `NOT MATERIALIZED`
    hints). See [window functions](window-functions.md) for CTEs staging
    time-series pipelines.

## Recursive CTEs — know it exists

`WITH RECURSIVE` is the one thing subqueries **can't** express: a CTE that
references *itself*, so the query iterates. The shape is always an **anchor**
member (the base rows), `UNION ALL`, and a **recursive** member that joins back
to the CTE's own name — re-running, feeding each pass into the next, until it
yields no new rows.

```sql
-- sequence generation (rows in no table): 1..10
WITH RECURSIVE seq(n) AS (
    SELECT 1                                                 -- anchor
    UNION ALL
    SELECT n + 1 FROM seq WHERE n < 10                       -- recurse
)
SELECT n FROM seq;

-- hierarchy traversal: employee 1 and everyone under them
WITH RECURSIVE reports AS (
    SELECT id, manager_id FROM employees WHERE id = 1        -- anchor: root
    UNION ALL
    SELECT e.id, e.manager_id
    FROM employees e JOIN reports r ON e.manager_id = r.id   -- recurse down
)
SELECT * FROM reports;
```

Reach for it for self-referential hierarchies (org charts, category/comment
trees, dependency graphs) or generating a series — recognise the shape; it's not
worth drilling beyond that.
