# statsmodels

statsmodels is for **statistical inference**, not prediction. The distinction organises
everything else about it:

- [scikit-learn](../scikit-learn/estimators.md) asks *how well does this predict unseen
  data?* The deliverable is a prediction function; regularisation is on by default,
  because it helps the only thing being measured.
- statsmodels asks *what are the parameters, and how sure are we?* The deliverable is a
  coefficient table with standard errors, test statistics, confidence intervals, and
  residual diagnostics. Regularisation is off by default, because a shrunk coefficient has
  no standard error worth reporting.

That is why `LinearRegression` has no `.pvalues` and `sm.OLS` has no `cross_val_score`.
The second reason to reach for statsmodels is coverage: whole families scikit-learn lacks
— time series, mixed effects, survival analysis, quantile and robust regression, and a
large catalogue of hypothesis tests. Its lineage is R and econometrics, and it usually
mirrors the canonical R implementation down to the formula syntax.

## Model → Results

Nearly everything follows one pattern, and it is not scikit-learn's:

```python
import statsmodels.api as sm

mod = sm.OLS(y, sm.add_constant(X))   # data + specification, nothing estimated
res = mod.fit()                       # a NEW object holding the estimates
res.summary()
```

Keeping the two separate is what lets you call `mod.fit(cov_type="HC3")` twice and compare,
evaluate `mod.loglike(params)` at parameters of your choosing, or run a recursion at frozen
parameters without re-estimating.

The arguments are named for econometrics: **`endog`** (endogenous — the thing being
modelled, scikit-learn's `y`) and **`exog`** (exogenous — the regressors, scikit-learn's
`X`). These names appear in every signature and in `missing=` handling.

!!! warning "Two bugs that don't raise"
    **Argument order is reversed.** scikit-learn takes `model.fit(X, y)`; statsmodels takes
    `sm.OLS(y, X)` — *outcome first*. Both arguments are numeric arrays of compatible
    shape, so swapping them silently regresses `X` on `y`.

    **No intercept is added.** `sm.OLS(y, X)` fits through the origin. Call
    `sm.add_constant(X)`, or you get a plausible table with wrong coefficients and an
    inflated $R^2$. The formula API below does add one.

## Arrays or formulas

```python
import statsmodels.api as sm           # array API, capitalised classes
import statsmodels.formula.api as smf  # formula API, lowercase functions

res = sm.OLS(df["y"], sm.add_constant(df[["x1", "x2"]])).fit()
res = smf.ols("y ~ x1 + x2", data=df).fit()     # same estimator
```

The formula API builds the design matrix from an R-style string (via `patsy`, migrating to
`formulaic`), handling categorical encoding, interactions, and transformations
declaratively:

| Formula | Meaning |
|---|---|
| `y ~ x1 - 1` or `y ~ x1 + 0` | drop the intercept |
| `y ~ C(region)` | dummy-encode as categorical with a reference level |
| `y ~ C(region, Treatment("west"))` | choose the reference level |
| `y ~ x1:x2` | interaction only |
| `y ~ x1 * x2` | `x1 + x2 + x1:x2` |
| `y ~ np.log(x1)` | any callable in scope |
| `y ~ I(x1 + x2)` | `I()` protects literal arithmetic from formula operators |

The categorical handling is the real win — reference level chosen, coefficients labelled in
the summary, DataFrame untouched. It also composes with pandas:
[`df.pipe((smf.ols, "data"), formula=...)`](../../data/pandas/transforming/chaining.md).

## The results object

A consistent vocabulary across nearly every model:

```python
res.params, res.bse, res.tvalues, res.pvalues   # estimates and uncertainty
res.conf_int(alpha=0.05), res.cov_params()
res.fittedvalues, res.resid
res.llf, res.aic, res.bic, res.rsquared         # rsquared is OLS-family only
res.nobs, res.df_resid, res.df_model
```

Hypothesis tests take **restriction strings**, which beats building contrast matrices by
hand:

```python
res.t_test("x1 = 0")
res.f_test("x1 = x2 = 0")
res_big.compare_lr_test(res_small)
```

`summary()` prints the coefficient block plus diagnostics — Omnibus and Jarque–Bera for
residual normality, Durbin–Watson for first-order autocorrelation, and the condition
number. Read the footnotes: a large condition number means multicollinearity (coefficients
individually unstable even when prediction is fine), and a Durbin–Watson far from 2 means
autocorrelated residuals, which invalidates the default standard errors.

!!! tip "`get_prediction`, not just `predict`"
    `res.predict(new_df)` gives point predictions. `res.get_prediction(new_df)` returns an
    object whose `.summary_frame()` separates the **confidence interval for the mean**
    (uncertainty about $\mathbb{E}[y \mid x]$, narrow) from the **prediction interval for
    an observation** (adds residual variance, much wider). Reporting the first when you
    meant the second badly understates uncertainty.

### `cov_type` — the default is not robust

```python
res = sm.OLS(y, X).fit(cov_type="HC3")
res = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
res = sm.OLS(y, X).fit(cov_type="cluster", cov_kwds={"groups": firm_id})
```

- `'nonrobust'` (default) assumes homoskedastic, independent errors.
- `'HC0'`–`'HC3'` — heteroskedasticity-consistent (White); `HC3` for finite samples.
- `'HAC'` — heteroskedasticity- and autocorrelation-consistent (Newey–West), needs
  `maxlags`. See [Metric Standard Errors](../../finance/metric-standard-errors.md).
- `'cluster'` — clustered by group, needs `groups`.

Point estimates never change; only the standard errors, $t$-statistics, and $p$-values do.
Since inference is the whole reason to be here, this is the main decision, not polish.

## What's in the box

**Regression** — `OLS`, `WLS`, `GLS`, `GLSAR`; `GLM` (one class covering logistic, Poisson,
Gamma and more via `family=sm.families.Binomial()`, with full inference attached — often
the right answer when someone reaches for a classifier out of habit); `Logit`, `Probit`,
`MNLogit`, `OrderedModel`; count models including `NegativeBinomial` and zero-inflated
variants; `RLM` (robust M-estimators); `QuantReg` (model the median or the 10th percentile
rather than the mean); `MixedLM` (random intercepts and slopes); `PHReg` and
`SurvfuncRight` for survival analysis.

**Time series** — `statsmodels.tsa`, the deepest part of the library and the part with no
scikit-learn equivalent:

- Models — `ARIMA`, `SARIMAX` (seasonal, with exogenous regressors), `AutoReg`, `VAR`,
  `VECM`, `ETSModel`, `UnobservedComponents`, `DynamicFactor`, and
  [`MarkovRegression`](markov-regression.md).
- Diagnostics — `acf`, `pacf`, `adfuller` (Augmented Dickey–Fuller unit-root test), `kpss`,
  `acorr_ljungbox`, `grangercausalitytests`, `coint`.
- Decomposition — `seasonal_decompose`, `STL`, `hpfilter`.
- `statsmodels.tsa.statespace` — SARIMAX, `UnobservedComponents`, and `DynamicFactor` all
  sit on one Kalman filter engine exposed as `MLEModel`, which you can subclass to estimate
  a custom linear-Gaussian state space model by maximum likelihood. Underused.

Time-series results add `res.forecast(steps)`, `res.get_forecast(steps)` (with intervals),
`res.simulate()`, and — for state space models — `res.append()` / `res.apply()`, which
carry fitted parameters onto new observations without re-estimating.

**Tests and diagnostics** — `statsmodels.stats`:

```python
from statsmodels.stats.diagnostic import het_breuschpagan, acorr_ljungbox
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.anova import anova_lm
from statsmodels.stats.power import TTestIndPower
```

Heteroskedasticity and autocorrelation tests, normality tests, variance inflation factors,
multiple-comparison corrections (Bonferroni, Benjamini–Hochberg), analysis of variance
(ANOVA) tables, weighted descriptive statistics, power and sample-size calculations,
proportion tests, contingency tables. `multipletests` and the power module are the most
needed and least known.

**Elsewhere** — `statsmodels.multivariate` (principal component analysis with inference,
factor analysis, MANOVA, canonical correlation); `statsmodels.graphics` (`qqplot`,
`plot_acf`, `influence_plot`, `plot_regress_exog` — diagnostic plots that understand the
results object); `statsmodels.datasets`.

## Gotchas

- **Missing data** — `missing='none'` is the default and propagates `NaN` into garbage.
  Pass `missing='drop'` or clean beforehand; for time series, dropping interior rows
  silently changes what "one period" means.
- **Pandas in, pandas out** — pass a `Series`/`DataFrame` and `params`, `fittedvalues`, and
  `resid` come back labelled and index-aligned.
- **`fit_regularized()`** gives elastic net on OLS and GLM, but the result carries no
  standard errors or $p$-values: post-selection inference is not valid and the library
  does not pretend otherwise. Regularised *prediction* belongs in scikit-learn.
- **No pipelines, no cross-validation** — there is no `fit`/`transform` protocol, so
  leak-safety is on you. A good argument for preprocessing in a
  [scikit-learn Pipeline](../scikit-learn/pipelines.md) and bringing the clean matrix over.
- **`summary()` is for humans** — read `res.params` and `res.bse` programmatically.
  `statsmodels.iolib.summary2.summary_col` builds side-by-side tables across several
  fitted models, the standard way to produce a regression table.
- **Version churn in `tsa`** — older tutorials use `sm.tsa.ARMA` and the legacy `ARIMA`,
  both removed in favour of `statsmodels.tsa.arima.model.ARIMA` and `SARIMAX`. Check import
  paths against the current docs rather than copying a blog post.

## The loop

```python
import numpy as np
import statsmodels.formula.api as smf
from statsmodels.stats.diagnostic import het_breuschpagan

res = smf.ols("sales ~ price + np.log(spend) + C(region)", data=df).fit(cov_type="HC3")
print(res.summary())

lm, lm_p, f, f_p = het_breuschpagan(res.resid, res.model.exog)   # was HC3 warranted?
res.f_test("C(region)[T.north] = C(region)[T.south] = 0")        # joint test on a block
pred = res.get_prediction(new_df).summary_frame(alpha=0.05)
```

Specify, fit, *read the diagnostics*, choose the covariance estimator in light of them,
then test and predict. That loop is what you are buying.

## Related

- [MarkovRegression](markov-regression.md) — the regime-switching models, in detail
- [The Estimator API](../scikit-learn/estimators.md) — the other convention, and the one the argument order is reversed from
- [Metric Standard Errors](../../finance/metric-standard-errors.md) — `OLS` on a constant as the tidiest route to a HAC standard error
- [Chaining](../../data/pandas/transforming/chaining.md) — `.pipe` with a keyword tuple, for routing a DataFrame into `data=`
