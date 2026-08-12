---
tags:
  - performance
---

# Pandas — Parquet

**Apache Parquet** is a binary, columnar, self-describing file format — the analytics-standard replacement for CSV, read/written by pandas, Polars, DuckDB, Spark, and Arrow alike. For persisting a DataFrame you'll re-load, it beats CSV on nearly every axis. Three defining properties, all from storing data **column-by-column**:

- **Columnar** — one column's values sit contiguously, so a query touching few columns reads only those bytes.
- **Compressed** — a column is one type with similar values → compresses hard (typically 5–20× smaller than CSV).
- **Self-describing** — the schema lives in the file, so [dtypes](dtypes.md) (`datetime64`, `category`, nullable `Int64`) round-trip exactly with no re-parsing.

!!! note "Row-oriented vs column-oriented"
    A CSV/row store writes `row0(a,b,c) row1(a,b,c)…` — good for "fetch whole record N" (transactional). Parquet writes `all-a, all-b, all-c` — good for "sum column `a` across all rows" (analytical). The layout *is* the workload you optimise for.

## Internal structure

```
File
├── Row group 1        # horizontal slice of rows; the unit of parallelism
│   ├── Column chunk: symbol   # → Pages (encode/compress unit)
│   └── Column chunk: ret      # → stores min/max/null stats
├── Row group 2 …
└── Footer             # schema + per-row-group per-column stats + offsets
```

Columnar layout buys two mechanical wins:

- **Column pushdown (projection)** — read 3 of 50 columns → touch only those 3 columns' bytes.
- **Predicate pushdown** — each row group's footer records column **min/max**, so a reader filtering `date >= '2024-06-01'` **skips** whole row groups that can't match. Sort by the column you filter on to make the stats tight.

## From pandas

```python
df.to_parquet('trades.parquet', compression='zstd', index=False)
df = pd.read_parquet('trades.parquet')                       # whole file

df = pd.read_parquet('trades.parquet', columns=['date', 'ret'])          # column pushdown
df = pd.read_parquet('trades.parquet',
                     filters=[('date', '>=', '2024-06-01')])             # predicate pushdown
```

- **Engine:** `pyarrow` (default, built on Apache Arrow) or `fastparquet` — `pip install pyarrow`.
- **`columns=` / `filters=`** are how you *cash in* the columnar wins; a bare `read_parquet(path)` reads everything.
- **`index=False`** skips writing the DataFrame index as a stored column.
- **Compression:** `snappy` (default, fast) for hot data; `zstd` (better ratio) increasingly the recommended default; `gzip` for cold archival.

## Partitioning

A **partitioned dataset** is a directory tree encoding a column's value in the *path*, so filtering skips whole subtrees (Hive-style):

```python
df.to_parquet('dataset/', partition_cols=['year', 'symbol'])
# dataset/year=2024/symbol=AAPL/part-0.parquet
pd.read_parquet('dataset/', filters=[('year', '=', 2024)])   # reads only that subtree
```

Partition on a **low-cardinality** column you filter on (date, region). Partitioning by a high-cardinality id makes millions of tiny files.

!!! warning "Immutable, binary, and the small-files problem"
    Parquet can't be appended to, edited in place, or `grep`/`tail`ed — a file is effectively immutable; you write *new* files (often new partitions) and let readers union them. For append-as-you-go or human inspection use [JSONL](../../python/libraries/jsonl.md) or a database, converting to Parquet in batches. And avoid many tiny files (over-partitioning, frequent small writes) — per-file overhead dominates; compact into fewer, larger files (~128 MB+ row groups).

## When to use it

- **Yes:** persisting DataFrames to re-load (faster/smaller/typed and portable, unlike Python-only `pickle`); analytical queries over medium-to-large tables.
- **No:** append-heavy logs, streaming records, human inspection, tiny configs → JSONL, a database, or CSV/JSON.
