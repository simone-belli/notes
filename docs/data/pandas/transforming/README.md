# Pandas — Transforming

Operations that reshape or combine a frame, and the chaining idiom that composes them.

:material-text-box-outline: **[Apply](apply.md){ .lvl-intermediate }**
:   Running a Series function over a frame — `axis` semantics, return-shape rules, `apply` vs `agg`/`transform`/`pipe`/`map`

:material-text-box-outline: **[Method Chaining](chaining.md){ .lvl-intermediate }**
:   Method chaining — `.assign`, `.pipe`, `.query`

:material-card-bulleted-outline: **[Chain Operations — Catalog](chaining-catalog.md){ .lvl-advanced }**
:   Catalog of common chain operations: astype, rename, filter, sort, groupby-agg, `to_frame`

:material-text-box-outline: **[GroupBy](groupby.md){ .lvl-basic }**
:   Split-apply-combine — `agg`, `transform`, `filter`, `apply`; multi-key groups, fast paths and keywords

:material-text-box-outline: **[Merge](merge.md){ .lvl-basic }**
:   SQL-style joins — `how` (inner/left/outer), `on`/`left_on`/`right_on`, the fan-out trap and `validate=`

:material-text-box-outline: **[Reshaping](reshaping.md){ .lvl-intermediate }**
:   Long vs wide; `stack`/`unstack` to rotate index↔columns; `pivot`, `pivot_table`, `melt`

:material-text-box-outline: **[Window Operations](windows.md){ .lvl-advanced }**
:   `shift`/`rolling`/`expanding` = SQL `LAG`/`ROWS BETWEEN`/`UNBOUNDED PRECEDING`; the off-by-one and partition reflexes
