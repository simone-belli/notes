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
| Attach timezone | `s.dt.tz_localize('UTC')` |
| Convert timezone | `s.dt.tz_convert('America/New_York')` |
| Pass to Python lib | `ts.to_pydatetime()` |
| Missing value | `pd.NaT` |
| Time-based groupby | `.resample('1D')` on DatetimeIndex |
| Lag by rows | `s.shift(1)` |
| Lag by real time | `df.shift(freq='1D')` |
