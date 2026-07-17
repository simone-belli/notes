---
quiz: detail
---

# JSON Lines (JSONL)

One JSON object per line. Append-friendly, streamable, human-readable — no infrastructure required. Uses [`pathlib.Path`](../language/stdlib/pathlib.md) for file access.

```
{"symbol": "AAPL", "qty": 10.0, "price": 182.5}
{"symbol": "MSFT", "qty": 5.0, "price": 310.0}
```

---

## Why JSONL over a JSON array

- **Append**: `file.write(line + "\n")` — no rewrite of the whole file.
- **Stream**: `for line in file` — O(1) memory regardless of file size.
- **Inspect**: `grep`, `head`, `tail` just work.

A plain JSON array `[...]` requires loading and rewriting the whole file to append.

---

## With Pydantic

[Pydantic](pydantic/pydantic.md) models serialise and validate for free via `model_dump_json()` and `model_validate_json()` — faster than `json.dumps(model.model_dump())` because they skip the intermediate dict.

```python
from pathlib import Path
from pydantic import BaseModel

class Trade(BaseModel):
    symbol: str
    qty: float
    price: float

PATH = Path("trades.jsonl")

def add(trade: Trade) -> None:
    with PATH.open("a", encoding="utf-8") as f:
        f.write(trade.model_dump_json() + "\n")

def get_all() -> list[Trade]:
    if not PATH.exists():
        return []
    with PATH.open(encoding="utf-8") as f:
        return [Trade.model_validate_json(l) for l in f if l.strip()]
```

---

## Edge cases

**Missing file** — `open("a")` creates the file on the first write; `get_all` returns `[]` before the file exists. No pre-creation needed.

**Empty file** — `if l.strip()` filters blank lines; `get_all` returns `[]` cleanly.

**Corrupt last line** — a killed write can leave a partial JSON line. Wrap `model_validate_json` in a `try/except` if resilience matters:

```python
rows = []
for l in f:
    if l.strip():
        try:
            rows.append(Trade.model_validate_json(l))
        except Exception:
            pass  # skip corrupt line
```

---

## How `for line in f` works

A file object implements the iterator protocol (`__iter__` / `__next__`): each `__next__` call reads up to the next `\n` and returns that string, including the newline. At EOF it raises `StopIteration`.

```python
with path.open(encoding="utf-8") as f:
    for line in f:
        print(repr(line))   # "foo\n", "bar\n", ...
```

- Lines include the trailing `\n` — `line.strip()` removes it (also handles `\r\n` on Windows and the last line if it has no newline).
- The file is read in OS-buffered chunks (~8 KB), not all at once — **O(1) memory** regardless of file size.
- The file stays open across `yield` suspensions inside a generator; it closes when the generator is exhausted or garbage-collected.

!!! note "readlines() vs iteration"
    `f.readlines()` or `list(f)` load all lines into memory at once. Prefer `for line in f` unless you genuinely need random access to lines.

---

## Streaming large files

```python
def iter_trades(path: Path):
    if not path.exists():
        return
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield Trade.model_validate_json(line)
```

The `with` block stays open between `yield` suspensions; the file closes once the generator is exhausted.

---

## JSONL vs alternatives

| Format | Append | Stream | Human-readable | Schema |
|---|---|---|---|---|
| JSONL | ✅ | ✅ | ✅ | optional (Pydantic) |
| JSON array | ❌ rewrite | ❌ load all | ✅ | optional |
| CSV | ✅ | ✅ | ✅ | ❌ flat/strings |
| SQLite | ✅ | ✅ | ❌ | ✅ |

!!! tip "When to switch"
    JSONL is the right choice up to a few hundred MB. Beyond that, or when you need queries/indexes, reach for SQLite (structured) or Parquet (columnar analytics).