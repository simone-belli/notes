# Pandas — Merge

`df.merge(other, ...)` (same as `pd.merge(left, right, ...)`) is the SQL-style relational join: match rows by **key columns** and stitch matched rows side by side. Distinct from [reshaping.md](reshaping.md)'s `concat` (glue by position/index, no key matching) and `df.join` (a thin wrapper that merges on the index).

## `how` — which keys survive

`how` decides which key values appear when a key is on one side but not the other (`L` = left keys, `R` = right keys):

| `how` | Keys kept | SQL | Unmatched cells |
|-------|-----------|-----|-----------------|
| `inner` (default) | `L ∩ R` | `INNER JOIN` | none — unmatched rows dropped |
| `left` | all of `L` | `LEFT OUTER` | right columns `NaN` |
| `right` | all of `R` | `RIGHT OUTER` | left columns `NaN` |
| `outer` | `L ∪ R` | `FULL OUTER` | missing side `NaN` |
| `cross` | every L × every R | `CROSS JOIN` | no key; cartesian |

- **`inner`** silently **drops** rows whose key has no partner — dangerous if you assumed every left row would match.
- **`left`** is the "enrich my table" join: keep every left row, look up extra columns from the right, `NaN` where no match. Use when the left is your spine (fact table) and the right is a lookup (dimension).

`indicator=True` adds a `_merge` column (`left_only`/`right_only`/`both`) — the fastest way to see what matched:

```python
trades.merge(ref, on='symbol', how='outer', indicator=True)['_merge'].value_counts()
```

## Specifying keys: `on` / `left_on` / `right_on` / `*_index`

- **`on='col'`** (or a list for a composite key) — column(s) with the **same name in both** frames must be equal.
- **`left_on` / `right_on`** — differently named keys: `left_on='ticker', right_on='symbol'`. **Both** columns survive in the output (drop the redundant one after).
- **`left_index=True` / `right_index=True`** — key on a frame's **index** instead of a column; mixable (`left_on='symbol', right_index=True`). `df.join` is the both-indexes shorthand.
- **No key args** — pandas joins on the intersection of shared column names (implicit; prefer explicit `on=`).

Overlapping non-key names get suffixed `_x`/`_y`; override with `suffixes=('_left', '_right')`.

!!! warning "Mismatched key dtypes match nothing"
    An `int64` key won't match an `object` `"123"` key — the merge returns zero matches (empty frame under `inner`) with no error. Check dtypes when a merge mysteriously loses all rows.

## The fan-out trap

A merge matches **every** left row against **every** right row sharing the key. If the key is **not unique on the right**, each left row fans out into one output row per match — a one-to-many join. Row count becomes `sum of right-matches per left row`, not `len(left)`.

Nothing errors. Every left value is now **duplicated** across the fanned-out rows, so a downstream `sum()` of a left column (notional, quantity, P&L) is **inflated** by the fan-out factor; means skew, weights stop summing to 1.

!!! danger "Catch it by reflex — assert or `validate=`"
    Every non-trivial merge, check the cardinality. Either compare row counts, or better, let pandas police it:

    ```python
    before = len(trades)
    out = trades.merge(ref, on='symbol', how='left')
    assert len(out) == before, f"fan-out: {before} -> {len(out)}"
    ```

`merge(..., validate=...)` raises `MergeError` if the cardinality is wrong — encode the invariant at the call site instead of a manual assert:

- `'one_to_one'` (`1:1`) — unique on both sides.
- `'one_to_many'` (`1:m`) — unique on the left.
- **`'many_to_one'` (`m:1`) — unique on the right; the guard for a lookup/enrichment `left` join** (the dimension table can't fan out your fact table).
- `'many_to_many'` (`m:m`) — no check.

```python
out = trades.merge(ref, on='symbol', how='left', validate='many_to_one')
```

Diagnosing a suspected fan-out:

```python
ref['symbol'].is_unique                 # False → fan-out risk
ref.groupby('symbol').size().max()      # worst-case fan-out factor per key
ref.drop_duplicates('symbol')           # fix when the right should be one-per-key
```
