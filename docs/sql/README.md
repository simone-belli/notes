# SQL

Declarative query patterns, with an explicit mapping to pandas equivalents.

<div class="grid cards" markdown>

-   :material-text-box-outline:{ .lg .middle } __[Aggregation: multi-key GROUP BY, HAVING, COUNT(DISTINCT), pivots](aggregation.md)__

    ---

    Multi-key grouping, WHERE vs HAVING, `COUNT(DISTINCT)`, and the conditional-aggregation (`SUM(CASE WHEN…)`) pivot idiom

-   :material-text-box-outline:{ .lg .middle } __[SQL basics: SELECT, JOIN, GROUP BY, subqueries, CTEs](basics.md)__

    ---

    SELECT/WHERE/ORDER BY/LIMIT, JOIN types and the fan-out trap, GROUP BY/HAVING, subqueries, first CTE

-   :material-text-box-outline:{ .lg .middle } __[Modifying data: INSERT, UPDATE, DELETE, upsert](modifying-data.md)__

    ---

    Writing rows: `INSERT`/`UPDATE`/`DELETE`, the missing-`WHERE` trap, and replacing a row via upsert (`ON CONFLICT`) vs `REPLACE`

-   :material-card-bulleted-outline:{ .lg .middle } __[sqlite3 CLI](sqlite3-cli.md)__

    ---

    `sqlite3` shell: dot-commands, output modes, non-interactive use, `.sqliterc`

-   :material-text-box-outline:{ .lg .middle } __[Window functions & CTEs](window-functions.md)__

    ---

    `OVER`/`PARTITION BY`/frames mapped to `groupby`/`shift`/`rolling`; CTEs; time-series patterns

</div>
