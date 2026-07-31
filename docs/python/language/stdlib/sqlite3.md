# sqlite3

`sqlite3` is the standard-library module for **SQLite** — a serverless,
single-file SQL database engine bundled with CPython (no install, no server).
Reach for it when you want real SQL semantics (transactions, joins, indexes,
constraints) without the weight of a database server: caches, app storage, test
fixtures, prototypes, ad-hoc analysis.

It implements **DB-API 2.0** (PEP 249), the standard interface nearly every
Python SQL driver follows — so `connect → cursor → execute → fetch` transfers
directly to `psycopg2` (PostgreSQL), `mysqlclient`, etc. Same engine and file
format as the [sqlite3 CLI shell](../../../sql/sqlite3-cli.md).

## Core objects

```python
import sqlite3

conn = sqlite3.connect("app.db")   # Connection: open DB + current transaction
cur = conn.cursor()                 # Cursor: runs SQL, holds result rows
cur.execute("SELECT name FROM users WHERE age > ?", (18,))
rows = cur.fetchall()               # list of tuples
conn.close()
```

- **Connection** — the file plus the transaction; owns `commit()`,
  `rollback()`, `close()`.
- **Cursor** — executes statements and streams results.
- `sqlite3.connect(":memory:")` makes an in-RAM database that vanishes on close
  (ideal for tests). A file DB is created on first *write*, not on open.

## Executing

| Method | Use for |
|--------|---------|
| `execute(sql, params)` | one statement |
| `executemany(sql, seq)` | same statement, many rows (bulk insert) |
| `executescript(text)` | multiple `;`-separated statements; **auto-commits** first |

`Connection.execute(...)` is sugar that makes a throwaway cursor for one-liners.

## Parameters — never string-format SQL

Use placeholders and pass values separately; the driver quotes/escapes them,
closing off **SQL injection**.

```python
cur.execute("SELECT * FROM users WHERE age > ? AND city = ?", (18, "Rome"))   # qmark
cur.execute("SELECT * FROM users WHERE age > :n", {"n": 18})                   # named
```

!!! warning "Single-value tuple needs a trailing comma"
    `(18)` is the integer `18`; the parameter sequence must be `(18,)`.

Placeholders bind **values**, not identifiers — you cannot parameterise a table
or column name.

## Reading results

```python
for row in cur.execute("SELECT id, name FROM users"):   # cursor is iterable — streams
    ...
```

- `fetchone()` → next row or `None`; `fetchmany(n)` → batch; `fetchall()` → all.
- Rows are tuples by default. Set `conn.row_factory = sqlite3.Row` for rows that
  index by name **and** position:

```python
conn.row_factory = sqlite3.Row
row = conn.execute("SELECT id, name FROM users").fetchone()
row["name"], row[0], dict(row)
```

## Transactions

Nothing is persisted until `conn.commit()`. By default (legacy behaviour) the
module opens a transaction implicitly before `INSERT`/`UPDATE`/`DELETE` but not
before `SELECT`/DDL. Use the connection as a [context
manager](../runtime/context-managers.md) for the clean pattern:

```python
with sqlite3.connect("app.db") as conn:
    conn.execute("INSERT INTO users(name) VALUES (?)", ("Ada",))
    # commit on clean exit, rollback on exception
```

!!! warning "The context manager commits — it does not close"
    `with sqlite3.connect(...) as conn` manages the transaction, not the
    connection's lifetime. Still call `conn.close()` (or use
    `contextlib.closing`) to release the file lock.

!!! note "Python 3.12+ `autocommit`"
    Python 3.12 added an `autocommit` attribute implementing proper PEP 249
    semantics; the default `LEGACY_TRANSACTION_CONTROL` keeps the old
    `isolation_level` behaviour for compatibility.

## Types

SQLite stores `NULL`/`INTEGER`/`REAL`/`TEXT`/`BLOB`, mapping to Python
`None`/`int`/`float`/`str`/`bytes`. Register **adapters**/**converters**
(with `detect_types=sqlite3.PARSE_DECLTYPES`) for richer types; the built-in
`datetime` adapters were deprecated in 3.12, so store ISO-8601 strings via
[`datetime`](datetime.md) yourself.

!!! note "SQLite typing is dynamic"
    Column types are advisory affinities, not constraints — a `TEXT` column can
    hold an integer, unlike PostgreSQL/MySQL.

## pandas bridge

For analysis, let pandas do the I/O instead of cursors:

```python
import pandas as pd
df = pd.read_sql_query("SELECT * FROM users WHERE age > ?", conn, params=(18,))
df.to_sql("users", conn, if_exists="append", index=False)
```

Write heavy filtering/[joins](../../../sql/basics.md) in SQL, hand the result to
pandas for the rest.

## Sharp edges

- **Exceptions** inherit from `sqlite3.Error`: `IntegrityError` (constraint),
  `OperationalError` (locked DB, bad SQL, missing table), `ProgrammingError`
  (API misuse).
- **Threads** — a connection isn't shareable across threads by default
  (`ProgrammingError`); give each thread its own, or pass
  `check_same_thread=False` and serialise access.
- **`PRAGMA`** is set via SQL: `conn.execute("PRAGMA foreign_keys = ON")`
  (off by default), `PRAGMA journal_mode = WAL` for read/write concurrency.
