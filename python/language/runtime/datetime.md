# Datetime

Converting between strings, integer timestamps, and `datetime.datetime` objects.

## Three approaches

### `strptime` — known format

```python
from datetime import datetime

dt = datetime.strptime("2024-06-21 14:30:00", "%Y-%m-%d %H:%M:%S")
```

Supply a format string using `strftime`/`strptime` codes. Raises `ValueError` on mismatch.

Common codes:

| Code | Meaning | Example |
|------|---------|---------|
| `%Y` | 4-digit year | `2024` |
| `%m` | zero-padded month | `06` |
| `%d` | zero-padded day | `21` |
| `%H` | 24h hour | `14` |
| `%M` | minutes | `30` |
| `%S` | seconds | `00` |
| `%f` | microseconds | `000000` |
| `%z` | UTC offset | `+0000` |
| `%I` | 12h hour | `02` |
| `%p` | AM/PM | `PM` |

### `fromisoformat` — ISO 8601 strings (Python ≥ 3.7)

```python
dt = datetime.fromisoformat("2024-06-21T14:30:00")
dt = datetime.fromisoformat("2024-06-21T14:30:00+05:30")
```

- Python 3.11+ handles trailing `Z` natively.
- On 3.10 and below: `s.replace("Z", "+00:00")` before parsing.

### `dateutil.parser.parse` — fuzzy / unknown format

```python
from dateutil import parser  # pip install python-dateutil

dt = parser.parse("June 21 2024 2:30pm")
```

Tries many formats automatically. Convenient for user input or heterogeneous sources; can silently misparse ambiguous strings like `01/02/03`.

## Which to use?

| Situation | Use |
|-----------|-----|
| Known, fixed format | `strptime` |
| ISO 8601 from an API / database | `fromisoformat` |
| Unknown / user-supplied format | `dateutil.parser.parse` |

## Timezone awareness

A `datetime` is either *naive* (no `tzinfo`) or *aware* (has `tzinfo`). Mixing them raises `TypeError`.

```python
from datetime import datetime, timezone

# naive
dt = datetime.strptime("2024-06-21 14:30", "%Y-%m-%d %H:%M")
dt.tzinfo  # None

# aware via format string
dt = datetime.strptime("2024-06-21 14:30 +0000", "%Y-%m-%d %H:%M %z")

# attach tz to a naive datetime (only safe if you know the tz)
dt = dt.replace(tzinfo=timezone.utc)
```

## Going the other way (datetime → string)

```python
dt.strftime("%Y-%m-%d")   # → "2024-06-21"
dt.isoformat()             # → "2024-06-21T14:30:00"
```

---

## Integer timestamps

A Unix timestamp is seconds since 1970-01-01 00:00:00 UTC. It has no timezone — that only enters when you convert it to a datetime.

### Seconds → datetime

```python
from datetime import datetime, timezone

ts = 1719000000

# Always pass tz= — without it, fromtimestamp returns naive local time
dt = datetime.fromtimestamp(ts, tz=timezone.utc)   # 2024-06-21 20:00:00+00:00

# Specific timezone
import zoneinfo
dt = datetime.fromtimestamp(ts, tz=zoneinfo.ZoneInfo("Europe/Rome"))
```

`datetime.utcfromtimestamp(ts)` returns a **naive** UTC datetime and is deprecated in Python 3.12. Avoid it.

### Millisecond timestamps (most APIs and financial data)

```python
ts_ms = 1719000000000          # e.g. from Binance, JavaScript Date.now()
dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
```

Quick sanity check: if the timestamp is > ~2 × 10¹⁰ it is almost certainly milliseconds, not seconds.

### datetime → integer timestamp

```python
dt = datetime(2024, 6, 21, 20, 0, 0, tzinfo=timezone.utc)
ts     = int(dt.timestamp())          # seconds  → 1719000000
ts_ms  = int(dt.timestamp() * 1000)  # milliseconds → 1719000000000
```

`timestamp()` on a **naive** datetime assumes local time — the same footgun as `fromtimestamp()`. Always use aware datetimes for round-trips.

### Resolution summary

| Unit | Example | Common source |
|------|---------|---------------|
| seconds | `1719000000` | POSIX, most DBs, HTTP headers |
| milliseconds | `1719000000000` | JS, Binance, most financial APIs |
| microseconds | `1719000000000000` | PostgreSQL |
| nanoseconds | `1719000000000000000` | Kafka, InfluxDB — `datetime` loses sub-µs precision |