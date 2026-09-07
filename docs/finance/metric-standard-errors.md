# Metric Standard Errors

Almost every performance number worth reporting — mean return, Mean Squared
Error (MSE), Quasi-Likelihood (QLIKE), Sharpe ratio — is a **sample mean of a
per-observation quantity**. That single fact is what gives each of them a
standard error (SE): the Central Limit Theorem (CLT) applies to the average, so
the metric inherits `SE = s / sqrt(n)` where `s` is the sample standard deviation
of the per-observation contributions.

```
θ̂ = (1/n) Σ g(x_t)        SE(θ̂) = std(g) / sqrt(n)
```

The only work is (a) writing the metric in that form, (b) fixing the SE up for
autocorrelation, and (c) handling the one metric that is a *ratio* of means
rather than a mean.

## The per-observation contribution

| Metric | `g(x_t)` | Shape |
|---|---|---|
| Mean return | `r_t` | mean |
| MSE | `e_t²` | mean |
| Mean Absolute Error (MAE) | `\|e_t\|` | mean |
| QLIKE | `σ²_t/h_t − log(σ²_t/h_t) − 1` | mean |
| Sharpe ratio | — | ratio of means |
| Root MSE (RMSE) | — | transform of a mean |

`e_t` is the forecast error, `h_t` the forecast variance, `σ²_t` a realised
variance proxy.

!!! note "Compute `g` first, aggregate second"
    Keeping the per-observation series around costs nothing and buys the SE, a
    histogram of contributions, and the paired test against another model. A
    codebase that only ever returns the scalar has thrown that away.

## Mean

The base case. For a return series `r`:

```python
mu = r.mean()
se = r.std(ddof=1) / np.sqrt(len(r))
```

- Annualising with `q` periods per year scales the mean by `q` and the SE by `q`
  — *not* by `sqrt(q)`. (It is the *volatility* that scales by `sqrt(q)`.)
- The `t`-statistic `mu / se` is the same number as an annualised Sharpe ratio
  times `sqrt(years)`, which is why a Sharpe of 1.0 over 3 years is only
  marginally significant.

## MSE and RMSE

```python
sq = (y - yhat) ** 2                      # per-observation contributions
mse, se = sq.mean(), sq.std(ddof=1) / np.sqrt(len(sq))
```

- The SE depends on the **fourth** moment of the errors, since `var(e²)` involves
  `E[e⁴]`. On heavy-tailed financial data the MSE's own SE is large and itself
  poorly estimated — a handful of days set both the metric and its uncertainty.
- RMSE is a transform of a mean, so use the delta method:
  `SE(RMSE) ≈ SE(MSE) / (2 · RMSE)`.

!!! warning "MSE ranks volatility forecasts by their worst days"
    Squared loss on variance weights errors by the level of variance, so the
    ranking of two volatility models is decided almost entirely by the crisis
    period in the sample. This is the reason QLIKE exists.

## QLIKE

The loss function for **volatility forecasts**, comparing a forecast variance
`h_t` against a realised variance proxy `σ²_t`:

```
QLIKE_t = σ²_t / h_t − log(σ²_t / h_t) − 1        ≥ 0, zero iff h_t = σ²_t
```

```python
ratio = sigma2 / h
qlike = (ratio - np.log(ratio) - 1)
q, se = qlike.mean(), qlike.std(ddof=1) / np.sqrt(len(qlike))
```

- **Scale-free.** It depends only on the *ratio*, so a quiet day and a crisis day
  with the same proportional error contribute equally. MSE does the opposite.
- **Asymmetric.** Under-forecasting variance is punished far harder than
  over-forecasting — the `σ²/h` term blows up as `h → 0`, the `log` term only
  grows logarithmically the other way. That asymmetry matches the economics: a
  risk model that under-states variance is the dangerous failure.
- **Robust to proxy noise** (Patton, 2011). MSE and QLIKE are the two common
  losses whose *ranking* of forecasts is unchanged when the true variance is
  replaced by a conditionally unbiased noisy proxy such as realised variance.
  Most other intuitive choices — loss on standard deviations, `log` errors,
  Mean Absolute Percentage Error (MAPE) — are not robust and can reverse the
  ranking.
- Dropping the constant `−1` and the `log σ²` term (neither depends on the
  forecast) recovers the more common textbook form `log h_t + σ²_t / h_t`. The
  normalised version above is preferred for reporting because it is non-negative
  and zero at a perfect forecast.

## Sharpe ratio

The exception: a **ratio** of two estimates, so the SE comes from the delta
method rather than the CLT directly. Under independent and identically
distributed (i.i.d.) returns (Lo, 2002):

```
Var(SR̂) ≈ (1 + SR²/2) / n           per-period SR

SE(SR_ann) ≈ sqrt(q / n)             q periods per year; the SR²/2 term is
                                     negligible at realistic Sharpe levels
```

Three years of daily data: `sqrt(252/756) ≈ 0.58`, so a reported 1.0 is
"1.0 ± 0.6". See [Tuning a Trading Strategy](../ml/concepts/strategy-tuning.md)
for why that interval, not the point estimate, is what belongs in a report —
and why the denominator is a scale-invariance concern rather than a noise one.

The same delta-method treatment covers every other mean-over-standard-deviation
statistic, including the ICIR in
[Information Coefficient](information-coefficient.md).

## Autocorrelation: the i.i.d. SE is usually too small

`std(g)/sqrt(n)` assumes independent contributions. That fails routinely:

- **Overlapping returns.** `h`-period forward returns sampled daily share `h−1`
  days of data, so consecutive observations are mechanically correlated.
- **Persistent forecast errors.** Volatility models miss regimes in runs, not
  independently — QLIKE and MSE contributions cluster.
- **Serial correlation in returns** from illiquidity or smoothed marks inflates
  Sharpe and deflates its SE at the same time.

The fix is a heteroskedasticity- and autocorrelation-consistent (HAC), or
Newey–West, standard error:

```
SE² = (1/n) [ γ₀ + 2 Σ_{k=1..L} (1 − k/(L+1)) γ_k ]      γ_k = lag-k autocovariance of g
```

Regressing the contributions on a constant is the tidiest way to get it — the
coefficient *is* the metric, and the reported SE is the HAC one:

```python
import numpy as np
import statsmodels.api as sm

res = sm.OLS(g, np.ones(len(g))).fit(cov_type="HAC", cov_kwds={"maxlags": L})
res.params[0], res.bse[0]        # the metric, and its HAC standard error
```

Rule-of-thumb bandwidth `L = floor(4 · (n/100)**(2/9))`; with overlapping
`h`-period returns use at least `L = h − 1`.

## Comparing two models: use the paired difference

Never compare two metrics by checking whether their confidence intervals
overlap. Both are computed on the *same* observations, so their errors are
highly correlated and the SE of the difference is much smaller than either
individual SE. Form the loss differential and test *it* — this is the
Diebold–Mariano (DM) test:

```python
d = loss_a - loss_b                                    # per-observation, paired
res = sm.OLS(d, np.ones(len(d))).fit(cov_type="HAC", cov_kwds={"maxlags": L})
res.params[0] / res.bse[0]                             # DM statistic, ~ N(0,1)
```

!!! warning "DM is invalid for nested models"
    When model B is A plus extra parameters, the differential is degenerate under
    the null and the statistic is undersized. Use Clark–West, or the
    Giacomini–White conditional test on genuinely out-of-sample forecasts from a
    fixed estimation scheme.

## Related

- [Tuning a Trading Strategy](../ml/concepts/strategy-tuning.md) — Lo's Sharpe SE in context, and selection bias on top of it
- [Information Coefficient](information-coefficient.md) — another mean/standard-deviation ratio with the same delta-method SE
- [Model Validation](../ml/concepts/model-validation.md) — the protocol the predictions being scored must come out of
- [Time-Series Validation](../ml/concepts/time-series-validation.md) — where overlapping labels come from in the first place
