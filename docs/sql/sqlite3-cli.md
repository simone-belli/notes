# sqlite3 CLI

The official command-line shell for SQLite. Unlike `psql`/`mysql`, there's
no server to connect to — a SQLite database is a single file, and the CLI
just opens it directly like a text editor opens a `.txt` file. To drive the
same engine from Python, see the
[`sqlite3` module](../python/language/stdlib/sqlite3.md).

```bash
sqlite3 mydata.db      # open (creates on first write, not on open)
sqlite3                # transient in-memory database
```

Quit with `.quit`, `.exit`, or Ctrl-D.

## SQL statements vs. dot-commands

Two kinds of input at the `sqlite>` prompt:

- **SQL statements** — end with `;`. Standard, portable SQL.
- **Dot-commands** — start with `.`, no semicolon, interpreted by the CLI
  itself (not sent to the SQL engine) — not portable to other SQL tools.

!!! warning "Forgetting the semicolon"
    A statement without `;` leaves the shell in a `...>` continuation
    prompt, silently waiting for more input rather than erroring — the
    classic "why did it hang" moment.

## Essential dot-commands

```
.tables                 -- list tables/views
.schema [table]          -- show CREATE TABLE statement(s)
.mode column|box|csv|json  -- output format (default is hard to read)
.headers on               -- print column names (off by default!)
.import data.csv table    -- bulk-load a CSV
.output file.txt | stdout -- redirect query output
.read script.sql          -- execute a SQL/dot-command file
.help                     -- list all dot-commands
```

`.schema` is usually the fastest way to check a table's columns/types
without writing a query.

## Non-interactive use

```bash
sqlite3 mydata.db "SELECT COUNT(*) FROM users;"   # one-shot query
sqlite3 mydata.db < setup.sql                      # pipe a script in
sqlite3 -csv -header mydata.db "SELECT * FROM users;"
```

Reach for this in scripts/cron/CI — same [CLI flag conventions](../python/language/stdlib/cli.md)
as most Unix tools (`-csv`, `-json`, `-header`, `-readonly`).

## Persisting settings

`~/.sqliterc` runs at startup like [`~/.zshrc`](../tools/shell/zsh.md) for a
shell — put `.mode column` / `.headers on` there instead of retyping them
every session. Skip with `-noninit`; override with `-init myfile.sql`.

!!! note "Foreign keys are off by default"
    SQLite doesn't enforce foreign-key constraints unless the session runs
    `PRAGMA foreign_keys = ON;` — deleting a parent row with dependent
    children silently succeeds otherwise.

Dot-commands aren't SQL — `.tables` has a SQL-native equivalent via the
system table: `SELECT name FROM sqlite_master WHERE type='table';`.
