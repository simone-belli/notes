# Pandas

:material-card-bulleted-outline: **[Chain Operations — Catalog](chaining-catalog.md)**
:   Catalog of common chain operations: astype, rename, filter, sort, groupby-agg

:material-text-box-outline: **[Method Chaining](chaining.md)**
:   Method chaining — `.assign`, `.pipe`, `.query`

:material-text-box-outline: **[Datetimes](datetimes.md)**
:   Timestamp, DatetimeIndex, .dt accessor, tz handling, resampling

:material-card-bulleted-outline: **[Display Formatting](display.md)**
:   Print formatting: display options, per-column formatters, DatetimeIndex, df.style

:material-text-box-outline: **[dtypes](dtypes.md)**
:   dtype system — nullable types, categoricals, StringDtype, pd.NA

:material-text-box-outline: **[GroupBy](groupby.md)**
:   Split-apply-combine — `agg`, `transform`, `filter`, `apply`; multi-key groups, fast paths and keywords

:material-text-box-outline: **[Indexing, Views and Copies](indexing.md)**
:   Views vs copies, SettingWithCopyWarning, `.loc` rules, Copy-on-Write

:material-text-box-outline: **[Iteration](iteration.md)**
:   `__iter__` asymmetry, `.items()`, `iterrows()` vs `itertuples()`, scalar access

:material-text-box-outline: **[Merge](merge.md)**
:   SQL-style joins — `how` (inner/left/outer), `on`/`left_on`/`right_on`, the fan-out trap and `validate=`

:material-text-box-outline: **[Reshaping](reshaping.md)**
:   `stack`/`unstack` to rotate index↔columns; vs `pivot`, `pivot_table`, `melt`

:material-card-bulleted-outline: **[to_dict()](to-dict.md)**
:   Convert DataFrame/Series to dicts: `orient` options, records for JSON, gotchas

:material-text-box-outline: **[Window Operations](windows.md)**
:   `shift`/`rolling`/`expanding` = SQL `LAG`/`ROWS BETWEEN`/`UNBOUNDED PRECEDING`; the off-by-one and partition reflexes
