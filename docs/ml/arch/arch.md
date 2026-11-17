# arch

`arch` is a Python library for modelling **time-varying volatility**, built around the
Autoregressive Conditional Heteroskedasticity (ARCH) family and its descendants such as
Generalized ARCH (GARCH). Returns are hard to predict in their mean, but their variance
clusters: calm days follow calm days. Anything that needs *tomorrow's* risk, such as
Value-at-Risk, volatility targeting, or [Kelly sizing](../../finance/kelly-criterion.md),
needs that forecast. [statsmodels](../statsmodels/statsmodels.md) has no GARCH models,
so `arch` fills the gap.

| Module | Holds |
|---|---|
| `arch.univariate` | Volatility models: mean + variance process + distribution |
| `arch.unitroot` | Unit-root, stationarity and cointegration tests |
| `arch.bootstrap` | Block bootstraps and multiple-comparison tests for forecasts |
| `arch.covariance` | Kernel long-run covariance estimators |

## A model is three parts

$$
\begin{aligned}
r_t &= \mu_t + \epsilon_t && \text{mean} \\
\epsilon_t &= \sigma_t e_t, \quad e_t \sim D(0, 1) && \text{distribution} \\
\sigma_t^2 &= f(\epsilon_{t-1}, \sigma_{t-1}^2, \dots) && \text{volatility process}
\end{aligned}
$$

Each part swaps independently, and the parameter table is grouped the same way.

- **Mean**: `ZeroMean`, `ConstantMean`, `ARX`, `HARX` (Heterogeneous Autoregression,
  the standard model for realised volatility), and `LS`.
- **Volatility**: `GARCH`, `ARCH`, `EGARCH`, `APARCH`, `FIGARCH`, `HARCH`, `EWMAVariance`
  (RiskMetrics, $\lambda = 0.94$, nothing estimated), and `ConstantVariance`.
- **Distribution**: `Normal`, `StudentsT`, `SkewStudent`, and `GeneralizedError`.
  Returns are fat-tailed, so a $t$ usually beats the normal default.

## GARCH(1,1) and GJR

$$
\sigma_t^2 = \omega + \alpha \epsilon_{t-1}^2 + \gamma \epsilon_{t-1}^2 \mathbb{1}[\epsilon_{t-1} < 0] + \beta \sigma_{t-1}^2
$$

- $\alpha$ is the reaction to yesterday's shock, and $\beta$ is the memory of
  yesterday's variance.
- Persistence is $\alpha + \gamma/2 + \beta$, which is typically $0.98$–$0.99$ on
  equities. A shock's half-life is $\ln 0.5 / \ln(\alpha + \gamma/2 + \beta)$.
- The long-run variance is $\bar\sigma^2 = \omega / (1 - \alpha - \gamma/2 - \beta)$.
- With $\gamma = 0$ this is plain GARCH. A positive $\gamma$ is the
  Glosten–Jagannathan–Runkle (GJR) asymmetry: bad news raises volatility more than
  good news. In `arch` it is the `o` order on `GARCH`, not a separate class.
  `power=1.0` on top of it gives Threshold ARCH (TARCH).

## Building and fitting

```python
from arch import arch_model

am = arch_model(100 * returns, mean="Constant", vol="GARCH", p=1, o=1, q=1, dist="t")
res = am.fit(disp="off")
print(res.summary())
```

Use the component classes when the strings can't express what you want:

```python
from arch.univariate import ARX, EGARCH, SkewStudent

am = ARX(100 * returns, lags=1)
am.volatility = EGARCH(p=1, o=1, q=1)
am.distribution = SkewStudent()
```

!!! warning "Scale to percent returns"
    The optimiser assumes values of about $1$, not $0.01$. On decimal returns,
    $\omega \approx 10^{-6}$ and the fit converges badly. `arch` warns with
    `DataScaleWarning`. Multiply by 100 yourself, or pass `rescale=True` and read the
    factor from `res.scale`. Either way, every output (variance forecasts included)
    stays on the rescaled data, so variance comes out in percent squared.

## The results object

```python
res.params, res.std_err, res.pvalues        # mu, omega, alpha[1], gamma[1], beta[1], nu
res.conditional_volatility                  # in-sample sigma_t
res.std_resid                               # e_t, which should look independent
res.loglikelihood, res.aic, res.bic
res.plot()
```

- The default `cov_type="robust"` gives Bollerslev–Wooldridge quasi-maximum-likelihood
  standard errors. They stay valid even when the distribution is wrong, so this default
  is better than statsmodels' non-robust one.
- To diagnose, run Ljung–Box on `res.std_resid**2`. Leftover autocorrelation in the
  squares means the volatility process is too simple.

## Forecasting

```python
import numpy as np

fc = res.forecast(horizon=5, start="2024-01-01", reindex=False)
vol = np.sqrt(fc.variance)              # columns h.1 ... h.5
annual = np.sqrt(252 * fc.variance)     # daily data
```

!!! note "Rows are forecast origins"
    The row dated $t$ holds forecasts *made at* $t$ for $t+1, \dots, t+5$. It is not
    the forecast *of* $t$. Without `start=`, only the last observation is an origin.
    With it, you get a whole path of $h$-step forecasts without looping.

- `fc.variance` is the conditional variance of $r_{t+h}$, so take the square root to
  get volatility.
- `method="analytic"` is the default. GARCH has a closed form at every horizon, but
  EGARCH and some others have one only at $h = 1$.
- `method="simulation"` draws shocks from the fitted distribution, and
  `method="bootstrap"` resamples the standardised residuals. Both expose
  `fc.simulations`, whose paths give quantiles and Value-at-Risk directly.

!!! tip "Out-of-sample without refitting"
    `am.fit(last_obs="2024-01-01")` estimates on data before the split only.
    `res.forecast(start="2024-01-01")` then filters through later data at those
    frozen parameters. Fitting on the full sample first would let the parameters see
    the test period. For fully causal forecasts, refit in a loop with
    `first_obs` / `last_obs` and warm-start with `starting_values=prev.params`.
    `am.fix(params)` builds a results object with no estimation at all.

Score competing forecasts with the quasi-likelihood
([QLIKE](../../finance/metric-standard-errors.md#qlike)) loss, not mean squared error.

## The other modules

```python
from arch.unitroot import ADF, DFGLS, KPSS, PhillipsPerron, ZivotAndrews
from arch.unitroot.cointegration import engle_granger
from arch.bootstrap import StationaryBootstrap, optimal_block_length, SPA, MCS

ADF(prices).pvalue            # each test: .stat, .pvalue, .critical_values, .summary()
```

- **`arch.unitroot`**
    - Augmented Dickey–Fuller (ADF), `DFGLS` (generalised least squares detrending,
      which has more power), Phillips–Perron, Zivot–Andrews (allows one break), and
      `VarianceRatio`.
    - `KPSS` (Kwiatkowski–Phillips–Schmidt–Shin) reverses the null: it tests for
      stationarity.
    - Cointegration: `engle_granger`, `phillips_ouliaris`, `DynamicOLS`, and
      `FullyModifiedOLS`.
- **`arch.bootstrap`**
    - An independent and identically distributed (i.i.d.) bootstrap destroys serial dependence. `StationaryBootstrap`,
      `CircularBlockBootstrap`, and `MovingBlockBootstrap` resample blocks instead.
    - `optimal_block_length` picks the block size.
- **Multiple comparisons on per-period losses.** These are the formal answer to data
  snooping across many [strategy variants](../concepts/validation/strategy-tuning.md).
    - `SPA` (Superior Predictive Ability) asks whether *any* model beats the benchmark.
    - `StepM` asks *which* models beat it.
    - `MCS` (Model Confidence Set) gives the set that can't be told apart from the best.
- **`arch.covariance.kernel`**: `Bartlett` (Newey–West), `Parzen`, and
  `QuadraticSpectral`. Bandwidth is chosen automatically, which makes them the
  building blocks of heteroskedasticity- and autocorrelation-consistent (HAC)
  errors.

## Gotchas

- **Persistence near 1** often means an unmodelled break in the long-run variance, not
  true long memory. See [structural breaks](../statsmodels/markov-fit-pitfalls.md#structural-breaks-and-few-transitions).
- **$t$ degrees of freedom near 2** (`nu`) means the variance barely exists.
- **`NaN` is not handled.** An interior gap also changes what "yesterday" means to
  the recursion.
- **`fit()` is chatty**, so pass `disp="off"`.
- **Composing with statsmodels.** Fit the mean there and pass the residuals to
  `arch_model(resid, mean="Zero")`, or estimate both jointly in `arch`, which is more
  efficient.

## Related

- [statsmodels](../statsmodels/statsmodels.md) — the mean-side counterpart, with ARIMA, state space, and Markov switching
- [Metric Standard Errors](../../finance/metric-standard-errors.md) — QLIKE for scoring volatility forecasts, and HAC errors
- [Kelly Criterion](../../finance/kelly-criterion.md) — position size inversely proportional to the forecast variance
