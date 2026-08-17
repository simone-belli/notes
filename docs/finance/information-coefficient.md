# Information Coefficient

The correlation between a signal's predictions and the returns those predictions
were trying to forecast. **Rank IC** uses Spearman rather than Pearson — the
Pearson correlation computed on the *ranks* of both series.

```
IC_t = spearman( pred_{i,t} , ret_{i,t→t+h} )   over the assets i at date t
```

- The horizon `h` must match the label the model was fit on.
- Predictions and returns must be aligned so `ret` is strictly *forward* of the
  information in `pred` — an IC computed on contemporaneous returns is a
  [leakage](../ml/concepts/data-leakage.md) check, not a performance metric.

## Cross-sectional vs time-series

- **Cross-sectional IC** (the default meaning) — one IC per date, correlating
  across the asset universe. Answers "did I rank today's names correctly?" and
  yields a *time series* `IC_t` to analyse.
- **Time-series IC** — one IC per asset, correlating across dates. What you use
  for a single instrument, where there is no cross-section.

## Computing it

```python
from scipy.stats import spearmanr

spearmanr(pred, fwd_ret).statistic          # a single rank IC
```

Panel, one IC per date, then the summary statistics:

```python
ic = df.groupby("date").apply(
    lambda g: g["pred"].corr(g["fwd_ret"], method="spearman")
)

ic.mean()                                    # mean IC
ic.mean() / ic.std(ddof=1)                   # ICIR, per period
ic.mean() / ic.std(ddof=1) * np.sqrt(252)    # annualised, daily rebalance
```

`ICIR` (information ratio of the IC) matters more than mean IC alone: a signal
with IC 0.03 every day beats one averaging 0.05 by alternating +0.30 and −0.24.

## Why rank rather than Pearson

- **Invariant to any monotone transform of the predictions.** The model's output
  scale, units, and calibration are irrelevant — only the ordering is scored. A
  ridge model and the same model with the coefficients doubled get identical rank
  IC. See [Tuning a Trading Strategy](../ml/concepts/strategy-tuning.md).
- **Bounded per-observation influence.** Pearson IC is driven by the tails; one
  6-sigma day can set the number. Moving any single observation changes rank IC
  by `O(1/n)`.
- **Costs magnitude information.** Rank IC scores the ordering only, so a signal
  that ranks well but misses *which* moves are large can post a healthy IC and
  still lose money. Read it alongside a return-weighted metric, never alone.

!!! note "Sign conventions and scale"
    IC is bounded `[-1, 1]`, and a consistently *negative* IC is a working signal
    with the sign flipped. Magnitudes are small by classifier standards: a real
    daily cross-sectional equity signal runs **0.02–0.05**, monthly factors
    perhaps 0.05–0.10.

!!! warning "An IC above ~0.15 is a bug report"
    On daily cross-sectional data that is very nearly always lookahead,
    misaligned timestamps, or a label that ended up in the features — not alpha.
    Check the alignment before celebrating.

## Fundamental Law of Active Management

```
IR ≈ IC × sqrt(breadth)
```

`breadth` = the number of independent bets per year. A weak signal applied
across many independent opportunities beats a strong one applied narrowly, which
is the formal case for wide universes and frequent rebalancing. The
"independent" qualifier does the real work: correlated names inflate the nominal
count without adding breadth.

## Caveats

- **Thin cross-sections are noisy.** IC on 15 names is mostly sampling error;
  stability wants `N` in the hundreds.
- **Ties collapse it.** A signal with few distinct values (bucketed scores,
  sparse predictions) produces heavy ties and a mechanically attenuated IC.
- **Equal-weights every asset**, regardless of liquidity or capacity, so it can
  reward ranking skill concentrated in names you cannot trade.
- **Ignores costs.** IC says nothing about turnover; two signals with equal IC
  can differ entirely in net return.

## Related

- [Kelly Criterion](kelly-criterion.md) — sizing once a signal's edge is measured
- [Tuning a Trading Strategy](../ml/concepts/strategy-tuning.md) — rank IC as a selection objective, and what to report instead
- [Model Validation](../ml/concepts/model-validation.md) — the protocol the predictions must come out of
