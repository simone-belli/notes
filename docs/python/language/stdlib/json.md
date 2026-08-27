# Canonical JSON

"Canonical" means equal data always produces byte-identical output. `json.dumps` is not canonical by default — dicts serialise in **insertion order**, so `{"a": 1, "b": 2}` and `{"b": 2, "a": 1}` give different text for the same data.

```python
import json

canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
blob = canonical.encode("utf-8")
```

| Flag | Default | Why change it |
|---|---|---|
| `sort_keys=True` | `False` | key order stops depending on how the dict was built |
| `separators=(",", ":")` | `(', ', ': ')` | drops cosmetic spaces — fewer bytes, one fixed choice |
| `ensure_ascii=False` | `True` | emits real UTF-8 rather than `é` escapes |

`ensure_ascii` is a choice, not a fix — `True` gives pure-ASCII output that survives any transport, `False` gives shorter readable output. Either is canonical as long as you always pick the same one.

## Why it matters

- **Hashing** — a content address, cache key, or deduplication ID for a dict.
- **Signing** — a signature covers bytes, so both parties must reproduce the same bytes.
- **Diffing** — no spurious version-control changes when a key is reinserted.
- **Comparing** — `dumps(a) == dumps(b)` as cheap structural equality on nested data.

```python
import hashlib

def fingerprint(obj) -> str:
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()

fingerprint({"b": 1, "a": 2}) == fingerprint({"a": 2, "b": 1})   # True
```

Without `sort_keys` those two hash differently — same data, different bytes. See [SHA-256](../../../tools/sha256.md) for the hash itself.

## What `sort_keys` does

- Sorts **recursively**, at every nesting level, not just the top.
- Sorts by Python string comparison, i.e. **Unicode code-point order** — `"Z" < "a"` and `"10" < "9"`.
- Does **not** reorder lists. Lists are ordered data; if their order is incidental, sort them yourself first.
- Non-string keys are coerced to strings *after* sorting, so a dict mixing types raises:

```python
json.dumps({1: "a", "a": 1}, sort_keys=True)
# TypeError: '<' not supported between instances of 'str' and 'int'
```

!!! warning "Floats are the real hazard"
    `1` and `1.0` serialise differently, and `NaN`/`inf` emit bare `NaN`/`Infinity` — **not valid JSON**, accepted silently by Python and rejected by strict parsers. Pass `allow_nan=False` to raise instead, and prefer integers (cents, basis points) or decimal strings in anything you intend to hash.

```python
json.dumps({"x": float("nan")})                    # '{"x": NaN}'  — invalid JSON
json.dumps({"x": float("nan")}, allow_nan=False)   # ValueError
```

## Round-tripping

Serialising is lossy: tuples become lists, integer keys become strings, and `set`, `datetime` and `Decimal` raise `TypeError`. The `default=` hook handles the last group:

```python
json.dumps(data, sort_keys=True, default=str)   # blunt but effective
```

!!! note "sort_keys is not RFC 8785"
    The JSON Canonicalization Scheme (JCS), standardised as Request for Comments (RFC) 8785, is the cross-language standard. Python's `sort_keys` differs on two points: JCS sorts by UTF-16 code-unit order (which diverges from code-point order only above the Basic Multilingual Plane) and mandates ECMAScript number formatting. Fine for fingerprints inside one codebase; use the `rfc8785` package when another implementation must agree byte-for-byte.

## Pretty-printing

```python
json.dumps(data, sort_keys=True, indent=2)   # readable and stable, not compact
```

Sorted keys give clean diffs for config files and test fixtures too. Don't expect the indented and compact forms to hash alike — pick one per purpose. For record-per-line files, see [JSON Lines](../../libraries/jsonl.md).
