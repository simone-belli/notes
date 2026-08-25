# SQL

Declarative query patterns, with an explicit mapping to pandas equivalents.

<div class="grid cards" markdown>

-   :material-text-box-outline:{ .lg .middle } __[Aggregation](aggregation.md)__

    ---

    Multi-key grouping, WHERE vs HAVING, `COUNT(DISTINCT)`, and the conditional-aggregation (`SUM(CASE WHEN…)`) pivot idiom

-   :material-text-box-outline:{ .lg .middle } __[SQL basics](basics.md)__

    ---

    SELECT/WHERE/ORDER BY/LIMIT, JOIN types and the fan-out trap, GROUP BY/HAVING, subqueries, first CTE

-   :material-text-box-outline:{ .lg .middle } __[Modifying data](modifying-data.md)__

    ---

    Writing rows: `INSERT`/`UPDATE`/`DELETE`, the missing-`WHERE` trap, and replacing a row via upsert (`ON CONFLICT`) vs `REPLACE`

-   :material-card-bulleted-outline:{ .lg .middle } __[sqlite3 CLI](sqlite3-cli.md)__

    ---

    `sqlite3` shell: dot-commands, output modes, non-interactive use, `.sqliterc`

-   :material-text-box-outline:{ .lg .middle } __[Subqueries & CTEs](subqueries.md)__

    ---

    Uncorrelated (derived table, scalar) vs correlated (`EXISTS`/`IN`), when a correlated subquery is a JOIN, deep nesting → chained CTEs, and recursive CTEs

-   :material-text-box-outline:{ .lg .middle } __[Window Functions](window-functions.md)__

    ---

    `OVER`/`PARTITION BY`/frames mapped to `groupby`/`shift`/`rolling`, and staging a window pipeline with a CTE

-   :material-text-box-outline:{ .lg .middle } __[Window Patterns](window-patterns.md)__

    ---

    Applied window shapes: top-N per group, gaps-and-islands, and time-series recipes built on them

</div>
