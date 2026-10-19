# predict

One method name, three unrelated signatures. Which `predict` you get depends on the model
family, and every family's default favours the flattering in-sample picture — so
[`statsmodels`](statsmodels.md) prediction is mostly a matter of knowing which default to
override.

## Model vs Results

```python
import statsmodels.api as sm

mod = sm.OLS(y, X)
res = mod.fit()

mod.predict(params, exog)     # at parameters you supply
res.predict(exog)             # at the fitted parameters
res.predict()                 # no argument → in-sample, == res.fittedvalues
```

`mod.predict(params, ...)` is how you evaluate a model at parameters estimated on an
earlier sample — see [Frozen parameters](frozen-parameters.md).

## Cross-sectional models

`res.predict(exog=None, transform=True)` for `OLS`, `WLS`, `RLM`, `QuantReg`.

`transform=True` only does something when the model was built with the formula API. The
results object then carries the design information, and a raw DataFrame is put through
every transform in the formula — `np.log(x)`, `C(category)`, interactions — in the fitted
column order.

With the array API there is no design information, so `exog` must already be a matrix in
exactly the fitted column order, constant included.

!!! warning "`add_constant` is not idempotent on new data"
    `sm.add_constant(new_X)` does **not** add a column if the frame's first column is
    already constant (`has_constant="skip"` is the default). The columns then shift by one
    and every coefficient is applied to the wrong feature, silently. Pass
    `has_constant="add"`, or use the formula API, where the bug cannot happen.

For uncertainty, `res.get_prediction(new)` beats `predict` — `.summary_frame()` separates
the interval for $\mathbb{E}[y \mid x]$ (`mean_ci_lower/upper`) from the interval for a new
observation (`obs_ci_lower/upper`), which adds $\hat\sigma^2$ and is much wider.

## Nonlinear-link models

`GLM` (Generalized Linear Model), `Logit`, `Probit`, `Poisson` return the mean on the
**response** scale, not the linear predictor:

$$
\hat\mu = g^{-1}(x^{\top}\hat\beta)
$$

```python
res.predict(X_new)                      # probabilities / expected counts
res.predict(X_new, which="linear")      # x'beta, the link scale
```

- `which="mean"` is the default; `which="linear"` gives $x^{\top}\hat\beta$. The older
  boolean `linear=True` is deprecated in favour of `which`.
- **No `predict_proba`, no labels.** `Logit.predict` returns $\hat p \in (0,1)$;
  thresholding is your code, and 0.5 is rarely the right cut. Unlike
  [scikit-learn](../scikit-learn/estimators.md), nothing here ever returns a class.
- `exposure=` and `offset=` are not remembered — pass them again at predict time, or a
  Poisson rate model quietly predicts counts for an exposure of one.

## Time-series models

```python
res.predict(start=None, end=None, dynamic=False)
res.get_prediction(start, end)     # .predicted_mean, .conf_int(), .summary_frame()
res.forecast(steps)                # sugar for predicting past the sample end
res.forecast(steps, exog=X_future) # required if the model has exog; needs `steps` rows
```

`start` and `end` are **index labels** (timestamps), not positions, when `endog` had a
pandas index; an `end` beyond the last observation extrapolates, so one call can straddle
in-sample and out-of-sample.

!!! warning "`dynamic=False` is one-step-ahead, not a forecast"
    In-sample, the default feeds the model the *true* lagged $y_{t-1}, y_{t-2}, \dots$ at
    every step. The fitted line tracks the data beautifully and says nothing about
    multi-step skill. `dynamic=True` — or `dynamic=k`, meaning from offset $k$ onward —
    substitutes the model's own predictions for those lags, so errors compound and the
    picture gets honest. See [Data Leakage](../concepts/data-leakage.md).

A model with `exog` cannot forecast without future regressor values — a useful reminder
that a feature you can't observe in advance improves the fit, not the forecast.

## Markov-switching results

[`MarkovRegression`](markov-regression.md) adds its own two arguments:

```python
res.predict(start, end, probabilities="predicted", conditional=False)
```

`conditional=True` returns one column per regime; otherwise the columns are averaged under
`probabilities`, whose default `"smoothed"` conditions on the **entire sample** and is a
lookahead in any evaluation loop.

## Related

- [statsmodels](statsmodels.md) — the Model→Results split these signatures hang off, and `get_prediction` intervals
- [Frozen parameters](frozen-parameters.md) — `mod.predict(params, …)` in a walk-forward loop
- [MarkovRegression](markov-regression.md) — the `probabilities` / `conditional` variant in context
- [Data Leakage](../concepts/data-leakage.md) — why every default here is the wrong one for a backtest
- [Time-Series Validation](../concepts/time-series-validation.md) — where a `dynamic=True` evaluation belongs
