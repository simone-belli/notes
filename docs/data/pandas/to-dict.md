# to_dict()

Convert a `DataFrame`/`Series` to native Python dicts/lists — e.g. before JSON
serialisation at an API boundary. Shape is chosen by `orient=`.

```python
df = pd.DataFrame({"x": [1, 2], "y": [3, 4]}, index=["a", "b"])
```

## DataFrame `orient` options

| `orient` | Result shape | Example |
|----------|--------------|---------|
| `"dict"` (default) | `{col: {index: val}}` | `{"x": {"a": 1, "b": 2}, "y": {...}}` |
| `"list"` | `{col: [vals]}` | `{"x": [1, 2], "y": [3, 4]}` |
| `"records"` | `[{col: val}, ...]` (one dict per row) | `[{"x": 1, "y": 3}, {"x": 2, "y": 4}]` |
| `"index"` | `{index: {col: val}}` | `{"a": {"x": 1, "y": 3}, "b": {...}}` |
| `"split"` | `{"index": [...], "columns": [...], "data": [[...]]}` | index/columns/data split out |
| `"tight"` | like `split` + `index_names`/`column_names` | round-trips a MultiIndex |
| `"series"` | `{col: Series}` | values stay as `Series`, not lists |

- `"records"` is the usual choice for JSON APIs — a list of row objects, drops
  the index.
- `"list"` is compact and columnar; good for rebuilding a `DataFrame`.
- `"split"`/`"tight"` are the round-trip formats: `pd.DataFrame.from_dict(d, orient="tight")`.

## Series

```python
s = pd.Series([1, 2], index=["a", "b"])
s.to_dict()          # {"a": 1, "b": 2}  — always {index: value}
```

## Gotchas

- Returns **native Python scalars**, not numpy types — `int`/`float`, so the
  result is JSON-serialisable. Timestamps become `Timestamp` objects, not
  strings; convert those yourself if the target must be pure JSON.
- Pass `into=` to change the container: `df.to_dict(orient="list", into=OrderedDict)`.
- Duplicate column names collapse in dict-keyed orients (`"dict"`, `"list"`,
  `"records"`) — later columns overwrite earlier ones.

## Related

- [Iteration](iteration.md) — row-by-row access without materialising a whole dict
- [FastAPI](../../python/libraries/fastapi/fastapi.md) — `df.to_dict("records")` to serialise rows at the endpoint boundary
