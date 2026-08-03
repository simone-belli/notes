---
quiz: detail
---

# Binance

World's largest crypto exchange by volume. A **centralised exchange (CEX)**: Binance holds custody of funds; trades update an internal database, not a blockchain. For data purposes only the exchange layer matters — the ecosystem (BNB Chain, NFTs, staking) is irrelevant.

See [market-data-apis.md](market-data-apis.md) for the quick-reference curl snippet.

---

## Market mechanics

**Order book**: every market has a sorted list of open bids (buy orders) and asks (sell orders). Market orders fill immediately against the best available price; limit orders rest in the book.

**Maker vs taker**: maker places a limit order that adds liquidity (lower fee ~0.02–0.1%); taker hits the book immediately (higher fee ~0.05–0.1%). The klines API exposes taker-buy volume separately, which serves as a proxy for buying aggression.

**Spot vs Perpetual Futures**:

| | Spot | Perpetual (PERP) |
|---|---|---|
| You own | Actual crypto | A contract |
| Leverage | 1× | Up to 125× |
| Expiry | None | None |
| Price anchor | N/A | Funding rate every 8 h |
| API host | `api.binance.com` | `fapi.binance.com` |

Most of Binance's *volume* sits in perpetual futures, not spot.

**Symbol format**: `BASE + QUOTE` — e.g. `BTCUSDT` = Bitcoin priced in USDT. Most liquid pairs are `*USDT`.

---

## Five most-traded cryptos (spot volume, 2023–2025)

| # | Symbol | Name | Notes |
|---|--------|------|-------|
| 1 | BTC | Bitcoin | Dominant; institutional flows |
| 2 | ETH | Ethereum | Smart contracts platform; DeFi hub |
| 3 | BNB | Binance Coin | Native token; used for fee discounts |
| 4 | SOL | Solana | High-throughput L1; large DeFi/NFT ecosystem |
| 5 | XRP | Ripple | Cross-border payments; large retail following |

USDT appears everywhere as the *quote* currency, not as a traded base asset.

---

## Klines (OHLCV) API — column reference

Each kline (candlestick) row is Open, High, Low, Close, Volume (OHLCV) for a time interval.

```
GET https://api.binance.com/api/v3/klines
    ?symbol=BTCUSDT&interval=1d&limit=500
```

Returns an array of arrays. Each inner array has **12 elements** (prices/volumes are strings — cast to float):

| Index | Field | Type | Description |
|-------|-------|------|-------------|
| 0 | `open_time` | int | Open timestamp (Unix **ms**) |
| 1 | `open` | str | Open price |
| 2 | `high` | str | High price |
| 3 | `low` | str | Low price |
| 4 | `close` | str | Close price |
| 5 | `volume` | str | Base asset volume (e.g. BTC count) |
| 6 | `close_time` | int | Close timestamp (Unix ms) |
| 7 | `quote_asset_volume` | str | Quote asset volume (e.g. total USDT value) |
| 8 | `number_of_trades` | int | Trade count |
| 9 | `taker_buy_base_asset_volume` | str | Base volume bought by takers |
| 10 | `taker_buy_quote_asset_volume` | str | Quote value of taker buys |
| 11 | `ignore` | str | Always `"0"` — discard |

!!! tip "Buy ratio as a signal for buying aggression"
    `taker_buy_base_asset_volume / volume` (columns 9 ÷ 5) gives the fraction of volume initiated by buyers. Values consistently above 0.5 indicate more aggressive buying; below 0.5 indicates selling pressure. This is a commonly used proxy in crypto market microstructure analysis.

**Key distinctions:**

- `volume` (5) = how many BTC changed hands. `quote_asset_volume` (7) = total USDT value — use this for cross-market comparisons.
- `taker_buy_base_asset_volume` (9) ÷ `volume` (5) = **buy ratio**. Above 0.5 → more buying aggression.
- `open_time` is the candle start (midnight UTC for 1d); `close_time` = open_time + interval − 1 ms.

Valid intervals: `1m 3m 5m 15m 30m 1h 2h 4h 6h 8h 12h 1d 3d 1w 1M`  
Max `limit`: 1000 per request. Paginate with `startTime` / `endTime` (Unix ms) for longer histories.

### Canonical pandas loader

```python
import requests, pandas as pd

def get_klines(symbol: str, interval: str = "1d", limit: int = 500) -> pd.DataFrame:
    r = requests.get(
        "https://api.binance.com/api/v3/klines",
        params={"symbol": symbol, "interval": interval, "limit": limit},
    )
    r.raise_for_status()
    cols = [
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_vol", "trades",
        "taker_buy_vol", "taker_buy_quote_vol", "ignore",
    ]
    df = pd.DataFrame(r.json(), columns=cols)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)  # see data/pandas/datetimes.md
    df.set_index("open_time", inplace=True)
    df.drop(columns=["close_time", "ignore"], inplace=True)
    float_cols = ["open","high","low","close","volume",
                  "quote_vol","taker_buy_vol","taker_buy_quote_vol"]
    df[float_cols] = df[float_cols].astype(float)
    df["trades"] = df["trades"].astype(int)
    return df
```

---

## Other useful endpoints (no key required)

```bash
GET /api/v3/ticker/price?symbol=BTCUSDT      # latest price
GET /api/v3/ticker/24hr?symbol=BTCUSDT       # 24 h rolling stats
GET /api/v3/depth?symbol=BTCUSDT&limit=20    # order book
GET /api/v3/exchangeInfo                     # all symbols + trading rules
GET https://fapi.binance.com/fapi/v1/klines  # futures klines (same schema)
```

---

## Rate limits

- Klines: 1–2 weight per call. Budget: **1200 weight/min**.
- Check `X-MBX-USED-WEIGHT-1M` response header.
- HTTP 429 = rate-limited; HTTP 418 = IP banned.

---

## Caveats

- Crypto only — no equities, FX, or commodities.
- Data starts mid-2017 (Binance launch). For older BTC history use Kraken/Bitstamp.
- Self-reported volume — wash trading is not independently audited.
