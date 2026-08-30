# Pandas

:material-text-box-outline: **[Datetimes](datetimes.md)**
:   Timestamp, DatetimeIndex, .dt accessor, tz handling, resampling

:material-card-bulleted-outline: **[Display Formatting](display.md)**
:   Print formatting: display options, per-column formatters, DatetimeIndex, df.style

:material-text-box-outline: **[dtypes](dtypes.md)**
:   dtype system — nullable types, categoricals, StringDtype, pd.NA

:material-text-box-outline: **[Filtering](filtering.md)**
:   Boolean masks, `&`/`|`/`~`, `isin`/`between`, `where`/`mask` vs `np.where`, NA in masks

:material-text-box-outline: **[Indexing, Views and Copies](indexing.md)**
:   Views vs copies, SettingWithCopyWarning, `.loc` rules, Copy-on-Write

:material-text-box-outline: **[Iteration](iteration.md)**
:   `__iter__` asymmetry, `.items()`, `iterrows()` vs `itertuples()`, scalar access

:material-text-box-outline: **[MultiIndex](multiindex.md)**
:   Hierarchical index of tuples — addressing with `.loc`/`.xs`/`IndexSlice`/level masks, adding/reordering levels, `reset_index`/`set_index`, sort-before-slice

:material-text-box-outline: **[Parquet](parquet.md)**
:   Columnar file format — column/predicate pushdown, row groups, `read_parquet`/`to_parquet`, partitioning

:material-card-bulleted-outline: **[to_dict()](to-dict.md)**
:   Convert DataFrame/Series to dicts: `orient` options, records for JSON, gotchas

:material-folder-outline: **[Transforming](transforming/)**
