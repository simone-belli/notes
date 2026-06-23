# Free Public Market Data APIs

## Quick reference

| Use case                       | API                      | Key required? |
|--------------------------------|--------------------------|---------------|
| EUR-based FX, daily            | Frankfurter              | No            |
| Broad FX coverage, daily       | fawazahmed0/currency-api | No            |
| Stock OHLCV                    | yfinance (Yahoo)         | No (unofficial)|
| Stock OHLCV, official          | Alpha Vantage            | Free signup   |
| Crypto OHLCV, high-volume      | Binance klines           | No            |
| Crypto OHLCV, broad coin list  | CoinGecko                | No (rate limited)|

---

## FX rates

### Frankfurter — ECB daily rates, no key

```bash
curl "https://api.frankfurter.app/latest?from=EUR&to=USD,GBP"
curl "https://api.frankfurter.app/2024-01-01..2024-03-31?from=USD&to=EUR"
```

~30 ECB-published currencies. Weekday updates only. No exotic EM, no crypto.

### fawazahmed0/currency-api — ~170 currencies, CDN-hosted

```
https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json
https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@2024-03-15/v1/currencies/usd.json
```

Mid-rates only, daily. No key. Includes some crypto pairs.

---

## Stock OHLCV

### yfinance (de facto standard)

```python
import yfinance as yf

df = yf.Ticker("AAPL").history(period="3mo")           # daily
df = yf.Ticker("AAPL").history(period="5d", interval="1h")  # intraday
data = yf.download(["AAPL", "SPY"], start="2024-01-01")     # multiple tickers
```

Returns a pandas DataFrame: `Open High Low Close Volume`. No key, but unofficial (reverse-engineered Yahoo Finance). Intraday limited to ~60 days.

### Alpha Vantage — free key, 25 req/day

```bash
curl "https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol=IBM&outputsize=compact&apikey=KEY"
```

Register free at alphavantage.co. `outputsize=compact` → last 100 days.

---

## Crypto OHLCV

### Binance klines — no key, best rate limits

```bash
curl "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=90"
```

Intervals: `1m 5m 15m 1h 4h 1d 1w`. Response is array of arrays:
`[open_time_ms, open, high, low, close, volume, ...]`

```python
import requests, pandas as pd

r = requests.get("https://api.binance.com/api/v3/klines",
                 params={"symbol": "BTCUSDT", "interval": "1d", "limit": 90})
cols = ["open_time","open","high","low","close","volume",
        "close_time","quote_vol","trades","_","__","___"]
df = pd.DataFrame(r.json(), columns=cols)
df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
df[["open","high","low","close","volume"]] = df[["open","high","low","close","volume"]].astype(float)
```

### CoinGecko — 10,000+ coins, rate-limited

```bash
curl "https://api.coingecko.com/api/v3/coins/bitcoin/ohlc?vs_currency=usd&days=30"
curl "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd"
```

Coin IDs are slugs (`bitcoin`, `ethereum`). Free tier: ~10–30 req/min — add `time.sleep(2)` in loops.

---

## Gotchas

- **Timestamps**: Binance = Unix ms, Kraken = Unix s, Yahoo = pandas Timestamps — parse carefully.
- **Intraday data** is usually restricted to recent history on free tiers.
- **Survivorship bias**: delisted tickers are inconsistent across free APIs.
- **Store raw responses** — free-tier quotas run out and replaying calls is wasteful.
