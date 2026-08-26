---
quiz: detail
---

# Datetimes

## The stack

```
Python      datetime.datetime    microsecond precision, tz-aware or naive
NumPy       np.datetime64[ns]    nanosecond precision, no timezone
Pandas      pd.Timestamp         nanosecond, tz-aware or naive
            pd.DatetimeIndex     array of Timestamps (column or index)
```

`pd.Timestamp` is both a subclass of [`datetime.datetime`](../../python/language/stdlib/datetime.md) and a wrapper around `np.datetime64[ns]`. It inherits all `datetime` methods while storing data as a 64-bit integer (nanoseconds since Unix epoch).

**Range limit:** nanosecond int64 restricts representable dates to ~1678–2262 CE. Dates outside this raise `OutOfBoundsDatetime`.

## `pd.Timestamp` — scalar

```python
ts = pd.Timestamp('2024-01-15 09:30:00')
ts.year, ts.month, ts.day    # 2024, 1, 15
ts.value                     # int64 nanoseconds since epoch

isinstance(ts, datetime.datetime)  # True

# timezone
ts_utc = pd.Timestamp('2024-01-15 09:30', tz='UTC')
ts_utc.tz_convert('America/New_York')

# missing datetime
pd.NaT          # like NaN for datetimes; pd.isna(pd.NaT) == True
```

## `pd.to_datetime()` — parsing

```python
pd.to_datetime('2024-01-15')                          # from string
pd.to_datetime(df['date_str'])                        # column of strings
pd.to_datetime(df['ts_ms'], unit='ms', utc=True)      # Unix ms (Binance format)
pd.to_datetime(df['date_str'], format='%Y-%m-%d')     # explicit format = faster
pd.to_datetime(df['date_str'], errors='coerce')       # bad values → NaT
```

Always pass `utc=True` when source is Unix timestamps — produces `datetime64[ns, UTC]` and keeps the whole column tz-aware.

## Datetime column dtype

```python
df['date'].dtype         # dtype('<M8[ns]')  — i.e. datetime64[ns]
df['date_utc'].dtype     # datetime64[ns, UTC]  — tz-aware variant
df['date'].iloc[0]       # pd.Timestamp(...)
```

## `.dt` accessor — vectorised operations

```python
s = df['date']            # datetime64 Series

s.dt.year                 # s.dt.month, .day, .hour, .minute, .second
s.dt.dayofweek            # 0=Mon … 6=Sun
s.dt.day_name()           # 'Monday', …
s.dt.date                 # Python date objects (drops time component)

s.dt.tz_localize('UTC')           # naive → aware (attach tz)
s.dt.tz_convert('America/New_York')  # aware → different tz

s.dt.floor('1h')          # round down
s.dt.ceil('1h')
s.dt.normalize()          # set time to midnight
```

## Naive vs aware — the one rule

!!! warning "Naive and aware timestamps cannot be mixed"
    Comparing or combining a naive `datetime64` with a tz-aware one raises `TypeError` at every layer (Python, NumPy, pandas). The fix is to commit to UTC from the moment data is loaded — pass `utc=True` to `pd.to_datetime()` and never produce naive datetimes for time-series data.

Naive and aware timestamps cannot be compared or combined — this holds at every layer (Python, NumPy, pandas). Pick one convention (UTC throughout is simplest) and apply it consistently from the moment data is loaded.

## Reading the timezone off an index

`DatetimeIndex.tz` reports which convention an index is actually using:

```python
df.index.tz        # ZoneInfo('America/New_York'), datetime.timezone.utc, or None
df.index.tzinfo    # alias, identical
str(df.index.tz)   # 'America/New_York' — the name, as a string

df['ts'].dt.tz     # same thing for a datetime column
```

- `None` means **naive**, which is not the same as UTC — pandas simply doesn't know.
- The value is a `tzinfo` object, not a string. Since pandas 2.0 zone names resolve to `zoneinfo.ZoneInfo` (older versions used `pytz`), so compare on `str(...)` rather than on the class.
- `df.index.dtype` shows the same fact: `datetime64[ns, UTC]` when aware, plain `datetime64[ns]` when naive.
- On a MultiIndex, pull the level out first: `df.index.get_level_values('ts').tz`.

!!! warning ".tz only exists on a DatetimeIndex"
    If the timestamps were never parsed, the index is a `RangeIndex` or `object` dtype and `.tz` raises `AttributeError`. Guard with `isinstance(df.index, pd.DatetimeIndex)`. The terser `getattr(df.index, "tz", None)` conflates "naive index" with "not a datetime index at all" — two different bugs.

Checking first is what makes the localize/convert pair below safe: pandas refuses to guess which one you meant.

## Localizing and converting an index

Two verbs cover every case. A naive timestamp is a **wall-clock reading**; an aware one is a **point in time**. `tz_localize` moves between those categories, `tz_convert` moves within the aware one.

| Direction | Call | What changes |
|-----------|------|--------------|
| naive → aware | `tz_localize(tz)` | Digits stay; the instant becomes defined |
| aware → naive | `tz_localize(None)` | Digits stay; the instant becomes undefined |
| aware → aware | `tz_convert(tz)` | Instant stays; digits shift |

Indexes are immutable — there is no `inplace=`, so assign the result back. The DataFrame carries the same methods, which reads better:

```python
df = df.tz_localize('UTC')        # equivalently: df.index = df.index.tz_localize('UTC')
df = df.tz_convert('Asia/Tokyo')
df = df.tz_localize(None)

df['ts'].dt.tz_localize(None)     # for a column rather than the index
```

Calling the wrong one raises `TypeError` (`Already tz-aware, use tz_convert…` / `Cannot convert tz-naive timestamps…`). To normalize an index of unknown provenance, branch on `.tz`:

```python
if df.index.tz is None:
    df.index = df.index.tz_localize('UTC')
else:
    df.index = df.index.tz_convert('UTC')
```

!!! warning "tz_localize(None) keeps *local* wall time, not UTC"
    Stripping the zone freezes whatever digits the index was displaying. An index shown in `America/New_York` becomes naive New York time, not naive UTC — data quietly rebased by several hours, with nothing that looks wrong. Always spell it `df.index.tz_convert('UTC').tz_localize(None)`.

### Daylight Saving Time (DST) hazards

Localizing *into* a DST zone is not always well defined, and both parameters default to raising:

```python
idx.tz_localize('Europe/Rome', ambiguous='infer')            # fall-back hour occurs twice
idx.tz_localize('Europe/Rome', nonexistent='shift_forward')  # spring-forward hour is missing
```

- `ambiguous` — `'raise'` (default), `'infer'` (from monotonic order; needs dense sorted data), `'NaT'`, or a boolean array where `True` picks the first occurrence.
- `nonexistent` — `'raise'` (default), `'shift_forward'`, `'shift_backward'`, `'NaT'`, or a `Timedelta`.

!!! tip "UTC has no DST — localize to UTC and both problems vanish"
    `tz_convert` never hits them either, since it starts from an unambiguous instant. Every DST headache lives in one place: localizing naive data into a zone that observes DST. Localize to UTC at ingest, convert to a display zone at the edges, and these parameters never appear in your code.

### Why go naive at all

Some destinations reject aware timestamps: `df.to_excel()` raises on them, some database drivers and older Parquet/HDF5 paths round-trip them badly, and matplotlib date axes and modelling libraries often prefer naive input. Convert to UTC before stripping, and record the convention somewhere — the timezone is now carried by agreement rather than by the data.

```python
naive = df.index.tz_convert('UTC').tz_localize(None)   # lossless round trip …
aware = naive.tz_localize('UTC')                       # … as long as both legs go via UTC
```

## Conversions

```python
ts.to_pydatetime()                   # pd.Timestamp → datetime.datetime
pd.Timestamp(datetime_obj)           # datetime.datetime → pd.Timestamp
ts.to_datetime64()                   # pd.Timestamp → np.datetime64[ns]
pd.Timestamp(np.datetime64('...'))   # np.datetime64 → pd.Timestamp
```

## Resampling — DatetimeIndex as time axis

```python
(df
 .set_index('date')
 .resample('1D').agg({'close': 'last', 'volume': 'sum'})
)
```

Common aliases: `'1min'`, `'1h'`, `'1D'`, `'1W'`, `'1ME'` (month-end), `'1QE'` (quarter-end).

## Lagging / shifting

`.shift()` has two modes on a DatetimeIndex — one moves values, one moves the index:

```python
df['close_lag1'] = df['close'].shift(1)     # move VALUES back 1 row (index fixed)
df['close_lead1'] = df['close'].shift(-1)   # forward 1 row (a lead)

df.shift(freq='1D')                          # move the INDEX forward 1 day (values fixed)
df.shift(3, freq='h')                        # index forward 3 hours
```

- `shift(periods)` — lag by **rows**; the first *N* rows become `NaN`. Use when
  there is one row per period.
- `shift(freq=...)` — lag by **real time**; re-timestamps every label, no `NaN`.
  Use for irregular/gappy series, then let index alignment match the lagged copy.
- Lag *within* groups so values don't leak across entities:
  `df.groupby('symbol')['close'].shift(1)`.

!!! tip "`.diff()` and `.pct_change()` are shift underneath"
    `s.diff(n)` is `s - s.shift(n)` and `s.pct_change(n)` is `s / s.shift(n) - 1`.
    For a positional lag on time series, [`resample`](#resampling-datetimeindex-as-time-axis)
    to a regular grid first if timestamps are uneven.

## Quick reference

| Need | Code |
|------|------|
| Parse strings | `pd.to_datetime(s)` |
| Parse Unix ms (Binance) | `pd.to_datetime(s, unit='ms', utc=True)` |
| Extract year/month/day | `s.dt.year` / `.dt.month` / `.dt.day` |
| Check an index's timezone | `df.index.tz` (`None` = naive) |
| Attach timezone | `s.dt.tz_localize('UTC')` |
| Convert timezone | `s.dt.tz_convert('America/New_York')` |
| Strip timezone (to naive UTC) | `df.index.tz_convert('UTC').tz_localize(None)` |
| Pass to Python lib | `ts.to_pydatetime()` |
| Missing value | `pd.NaT` |
| Time-based groupby | `.resample('1D')` on DatetimeIndex |
| Lag by rows | `s.shift(1)` |
| Lag by real time | `df.shift(freq='1D')` |
