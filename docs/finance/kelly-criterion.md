# Kelly Criterion

Formula for the fraction of a bankroll to bet/invest that **maximises long-run exponential growth rate**, given a positive-EV bet or strategy. Derived by John L. Kelly Jr. (1956) for noisy communication channels, later applied to gambling and trading.

!!! note "Not the same as maximising expected value"
    Maximising per-bet expected value pushes toward betting 100% of bankroll on any positive-EV wager — repeated, this guarantees eventual ruin. Kelly maximises the expected **log** of wealth instead, because wealth compounds multiplicatively (each bet's stake is a fraction of the *previous* outcome). Log-utility isn't an arbitrary risk preference here — it falls directly out of "maximise long-run compound growth."

## Binary bet formula

For a bet with win probability `p`, net odds `b` (win `b` units per unit staked), loss probability `q = 1-p`:

```
f* = p - q/b
```

Even-money special case (`b = 1`):

```
f* = 2p - 1
```

A 55% edge on a coin flip → bet 10% of bankroll.

## Continuous-return formula (trading)

For a strategy with expected return `μ` and variance `σ²` per period:

```
f* = μ / σ²
```

Size is proportional to edge and *inversely proportional to variance*, not volatility. Equivalently, in terms of Sharpe ratio `S = μ/σ`:

```
f* = S / σ
```

Two strategies with equal Sharpe ratios should get very different position sizes if their volatilities differ.

## Fractional Kelly

Full Kelly is growth-optimal but highly volatile (30%+ drawdowns are normal, not a sign something's wrong). The growth-rate-vs-`f` curve is concave and peaks at `f*`, so betting **half-Kelly** (`f*/2`) captures **~75%** of the max growth rate at roughly half the variance — a favorable trade most practitioners take. Betting `2×` Kelly drives long-run growth to *zero* despite positive per-bet EV; beyond that, growth turns negative (certain long-run ruin) even though every individual bet still has positive expected value.

!!! warning "Kelly is very sensitive to overestimated edge"
    `μ`/`p` enters the formula linearly and is usually estimated (backtest, live sample), not known. Overestimating edge and overbetting is far more costly than underbetting, because of the steep drop-off past `f*`. This is the main practical reason to haircut below the formula's output — not just to reduce variance.

## Why full Kelly is rarely used

- **Parameter uncertainty** — true `p`/`μ`/`σ²` are estimated, not known.
- **Non-stationarity** — real markets change regime; a measured edge may not persist.
- **Correlated positions** — the single-bet formula doesn't account for correlation across simultaneous bets. Multivariate form: `f* = Σ⁻¹μ`, where `Σ` is the covariance matrix — correlation reduces the total safe risk budget across positions.
- **Utility mismatch** — Kelly is indifferent to path (drawdowns) as long as terminal growth is maximised; real investors/institutions care about drawdowns directly (redemptions, margin calls).
- **Leverage/discreteness limits** — `f*` can exceed 1 (implying leverage) or be impractical given lot sizes and transaction costs.

In practice: compute full Kelly, apply a haircut (commonly half-Kelly), then cap further with hard portfolio risk limits regardless of the formula's output.

## Related ideas

- **[Information Coefficient](information-coefficient.md)** — where the `μ` this formula is so sensitive to comes from; the Fundamental Law (`IR ≈ IC × √breadth`) is the same edge measured before sizing.
- **Ergodicity** — Kelly is a canonical illustration of *ensemble average* vs *time average* diverging for multiplicative processes; the two only coincide for additive processes. This is why "maximise EV" and "maximise Kelly growth" disagree.
- **Gambler's ruin** — Kelly avoids fixed-stake ruin by always betting a fraction of *current* wealth, so bankroll approaches but never reaches zero from a single bad sequence (while `f* < 1`).
