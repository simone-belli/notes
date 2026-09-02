# SQL

Declarative query patterns, with an explicit mapping to pandas equivalents.

:material-text-box-outline: **[Aggregation](aggregation.md){ .lvl-intermediate }**
:   Multi-key grouping, WHERE vs HAVING, `COUNT(DISTINCT)`, and the conditional-aggregation (`SUM(CASE WHEN…)`) pivot idiom

:material-text-box-outline: **[SQL basics](basics.md){ .lvl-basic }**
:   SELECT/WHERE/ORDER BY/LIMIT, JOIN types and the fan-out trap, GROUP BY/HAVING, subqueries, first CTE

:material-text-box-outline: **[Modifying data](modifying-data.md){ .lvl-intermediate }**
:   Writing rows: `INSERT`/`UPDATE`/`DELETE`, the missing-`WHERE` trap, and replacing a row via upsert (`ON CONFLICT`) vs `REPLACE`

:material-card-bulleted-outline: **[sqlite3 CLI](sqlite3-cli.md){ .lvl-advanced }**
:   `sqlite3` shell: dot-commands, output modes, non-interactive use, `.sqliterc`

:material-text-box-outline: **[Subqueries & CTEs](subqueries.md){ .lvl-intermediate }**
:   Uncorrelated (derived table, scalar) vs correlated (`EXISTS`/`IN`), when a correlated subquery is a JOIN, deep nesting → chained CTEs, and recursive CTEs

:material-text-box-outline: **[Window Functions](window-functions.md){ .lvl-intermediate }**
:   `OVER`/`PARTITION BY`/frames mapped to `groupby`/`shift`/`rolling`, and staging a window pipeline with a CTE

:material-text-box-outline: **[Window Patterns](window-patterns.md){ .lvl-advanced }**
:   Applied window shapes: top-N per group, gaps-and-islands, and time-series recipes built on them
