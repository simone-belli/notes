# Modifying data

Data Manipulation Language (DML) beyond `SELECT` — writing rows. Each
statement affects rows chosen by a `WHERE` clause and reports a row count,
not a result set.

## INSERT

```sql
INSERT INTO employees (employee_id, name, salary)
VALUES (42, 'Ada', 95000);
```

Omitted columns take their default (or `NULL`). Insert many rows with
comma-separated tuples.

## UPDATE — change columns of existing rows

```sql
UPDATE employees
SET    salary = 95000, title = 'Senior Engineer'
WHERE  employee_id = 42;
```

!!! warning "A missing WHERE updates every row"
    `UPDATE`/`DELETE` without `WHERE` hits the whole table, with no undo
    outside a transaction. Run the filter as a `SELECT` first, then wrap the
    change in `BEGIN; ... COMMIT;` (or `ROLLBACK`) so you can back out.

## DELETE

```sql
DELETE FROM employees WHERE employee_id = 42;
```

`TRUNCATE TABLE employees` empties a whole table faster, but is not
transactional on all engines — treat it as unrecoverable.

## Replacing a row: upsert vs REPLACE

"Replace a row" usually means *insert it if new, overwrite if it exists* — an
**upsert**. The portable modern form is `INSERT ... ON CONFLICT`:

```sql
-- PostgreSQL / SQLite
INSERT INTO employees (employee_id, name, salary)
VALUES (42, 'Ada', 95000)
ON CONFLICT (employee_id)
DO UPDATE SET name = EXCLUDED.name, salary = EXCLUDED.salary;
```

- `ON CONFLICT (col)` names the unique/primary key that signals a collision.
- `EXCLUDED` is the pseudo-table holding the row you *tried* to insert — copy
  its values onto the existing row.
- `DO NOTHING` instead = insert only if absent. MySQL spells the whole thing
  `INSERT ... ON DUPLICATE KEY UPDATE ... VALUES(col)`.

`REPLACE INTO ...` (MySQL/SQLite) looks similar but is **delete-then-insert**:
unlisted columns reset to defaults, `ON DELETE` cascades and triggers fire, and
auto-increment IDs may change. Prefer `ON CONFLICT DO UPDATE` (patches in
place) unless you genuinely want the old row and its dependents gone.

!!! tip "Which command?"
    Row exists, just want new values → `UPDATE ... WHERE`. Want "overwrite it,
    or create it if missing" → `INSERT ... ON CONFLICT ... DO UPDATE`. The
    ANSI-standard `MERGE` (SQL Server, Oracle, PostgreSQL 15+) generalises this
    for bulk merges but is overkill for a single row.

See [SQL basics](basics.md) for the `SELECT`/`WHERE` clauses these share.
