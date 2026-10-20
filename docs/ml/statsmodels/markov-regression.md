# MarkovRegression

[`statsmodels`](statsmodels.md) implements Hamilton's Markov-switching regression —
regime-dependent coefficients driven by a latent chain — as `sm.tsa.MarkovRegression`:

$$
y_t = x_t^{\top}\beta_{s_t} + \varepsilon_t,
\qquad \varepsilon_t \sim \mathcal{N}(0, \sigma^2_{s_t}),
\qquad \Pr(s_t = j \mid s_{t-1} = i) = p_{ij}
$$

The statistical background — the Markov property, the Hamilton filter, filtering vs
smoothing, Expectation–Maximisation (EM) — is in
[Markov Processes](../concepts/markov-models.md); this is the API on top of it.

```python
import statsmodels.api as sm

mod = sm.tsa.MarkovRegression(
    y, k_regimes=2, exog=X, trend="n", switching_variance=True
)
res = mod.fit(search_reps=25)
```

Observations are conditionally independent given the state: no lagged $y$ on the
right-hand side. Autoregressive terms in Hamilton's mean-adjusted form need
[`sm.tsa.MarkovAutoregression`](markov-autoregression.md), a separate class, because
the lagged means break that structure.

## Constructor arguments

```python
MarkovRegression(endog, k_regimes, trend="c", exog=None, exog_tvtp=None,
                 switching_trend=True, switching_exog=True,
                 switching_variance=False, dates=None, freq=None, missing="none")
```

Everything but `dates`/`freq`/`missing` changes the model. The defaults are not what a
volatility-regime application wants.

- **`k_regimes`** — no automatic selection. Parameter count is $K(m+2) + K(K-1)$ for $m$
  switching regressors, and identification degrades faster than that count suggests.
  $K = 2$, occasionally 3; past that you are fitting noise.
- **`trend`** — `'c'` (default), `'n'`, `'t'`, `'ct'`, applied *in addition to* `exog`.
- **`exog`** — your design matrix. Lagging for causality is your job: pass `X.shift(1)` if
  the feature is only observable a period later.
- **`switching_trend`, `switching_exog`** — both default `True`. Both also accept a **list
  of booleans, one per column**, which is how you encode an actual hypothesis rather than
  letting everything float.

```python
mod = sm.tsa.MarkovRegression(
    y, k_regimes=2, exog=X,                  # X has three columns
    switching_exog=[True, False, False],     # only the first beta switches
)
```

!!! warning "`switching_variance` defaults to `False`"
    The most consequential default in the class. Left off, all regimes share one
    $\sigma^2$ and regimes can differ only in *mean* — and on daily returns the mean is
    drowned in noise. Volatility regimes are what most applications are actually about, so
    set `switching_variance=True`.

    Second trap: if `exog` already contains a constant (`sm.add_constant`), pass
    `trend="n"` or you get a duplicated column and a singular design.

### Time-varying transition probabilities

`exog_tvtp` makes the transition matrix a logistic function of covariates, so
$\mathbb{E}[D_i \mid z] = 1/(1 - p_{ii}(z_t))$ becomes time-varying and the parameter names
gain `.tvtp{k}` suffixes — those are **logit coefficients, not probabilities**.

```python
mod = sm.tsa.MarkovRegression(
    y, k_regimes=2, exog=X, exog_tvtp=sm.add_constant(Z)   # constant is NOT added for you
)
```

Without that constant column the model is forced to $p_{ij} = 1/K$ whenever $z_t = 0$,
which is never the intent.

## Fitting

```python
res = mod.fit(start_params=None, transformed=True, cov_type="approx", method="bfgs",
              maxiter=100, em_iter=5, search_reps=0, search_iter=5, disp=0)
```

The default path is **EM to initialise, then quasi-Newton to finish**: `em_iter=5`
iterations of Baum–Welch (robust far from the optimum, respects the constraints
automatically) hand off to BFGS on transformed parameters — probabilities logit-, variances
log-transformed, so the optimiser works on $\mathbb{R}^n$. That is what `transformed=`
refers to: `True` means the `start_params` *you* pass are in natural units.

!!! tip "`search_reps=0` is the default and is a local-optimum trap"
    The switching likelihood is multimodal, and one deterministic start lands in a local
    optimum routinely, not occasionally. `fit(search_reps=20)` draws 20 random starts, runs
    `search_iter=5` EM steps from each, and keeps the best — cheap next to the BFGS stage.
    Doing the restarts yourself also *measures* multimodality: if best and median
    log-likelihood differ wildly, $K$ is probably too large.

- **Scale returns to percent.** Daily returns are $O(10^{-3})$, so $\sigma^2$ is
  $O(10^{-6})$ and the log-variance parameters sit far from the rest in magnitude. `100 * r`
  fixes a surprising share of "it won't converge".
- **Check `res.mle_retvals["converged"]`.** `maxiter=100` is not generous for 15+
  parameters. `disp=True` while developing.
- **`cov_type`** — `'approx'` (numerical Hessian, default), `'opg'`, `'robust'`. None is
  trustworthy for a transition probability estimated near 0 or 1, which is the normal case
  for a persistent regime: the parameter sits at the edge of its space and
  [the asymptotics fail](../concepts/bayesian-markov-models.md). Judge persistence by
  expected duration, not by the standard error on `p[0->0]`.

## Reading the results

`res.params` is a `Series` with structured names — `p[i->j]` for transitions (only
$K(K-1)$ of them; the rest are implied), a `[regime]` suffix on switching parameters, no
suffix on the rest:

```
p[0->0]    0.9712     const[0]    0.0831     sigma2[0]   0.4455
p[1->0]    0.0405     const[1]   -0.1502     sigma2[1]   3.8821
```

Those names are for reading; to slice the vector in code — especially when a parameter
does not switch and several regimes share one slot — go through the
[`mod.parameters` index map](switching-parameters.md).

`res.summary()` prints this as a block per regime plus a transition block. Three
probability attributes, each `(nobs, k_regimes)` and a DataFrame when `endog` had a pandas
index:

```python
res.predicted_marginal_probabilities   # Pr(S_t | y_1:t-1)
res.filtered_marginal_probabilities    # Pr(S_t | y_1:t)     — causal
res.smoothed_marginal_probabilities    # Pr(S_t | y_1:T)     — uses the whole sample
```

Plus `res.regime_transition` (shape `(k, k, 1)`, or `(k, k, nobs)` with TVTP) and
`res.expected_durations` — $1/(1-p_{ii})$, the most interpretable number in the output.
Check it first: a regime with expected duration near 1 is a noise state, and usually means
$K$ is too large.

The three-dimensional transition array's storage convention is easy to get backwards.
Assert instead of remembering; the `p[i->j]` names are the authoritative reading.

```python
import numpy as np

P = res.regime_transition[:, :, 0]
assert np.allclose(P.sum(axis=0), 1.0)    # columns sum to one
```

Model comparison uses `res.llf`, `res.aic`, `res.bic`, `res.hqic` — with the caveat that
the likelihood-ratio test for $K$ vs $K+1$ has no $\chi^2$ null distribution, since the
extra regime's parameters are unidentified under the null and the null sits on the
parameter-space boundary.

### `predict`

There is no `fittedvalues`; [`res.predict(start, end, probabilities, conditional)`](predict.md)
is it.
`conditional=True` returns one column per regime; the default averages them,
$\hat{y}_t = \sum_i \Pr(S_t = i \mid \cdot)\, x_t^{\top}\hat\beta_i$.

!!! warning "The default weighting is smoothed"
    `res.predict()` with no arguments weights by probabilities conditioned on the **entire
    sample**. The fitted values track $y$ beautifully and mean nothing as a forecast. In
    any evaluation loop, pass `probabilities="predicted"` explicitly.

## Out-of-sample with frozen parameters

There is no [`append`/`apply`](frozen-parameters.md) here — those belong to the
state-space classes. The
walk-forward pattern goes through the **model's** `filter`, which evaluates the recursions
at parameters you supply without re-estimating (`mod.smooth(params)` adds the backward
pass):

```python
mod_tr = sm.tsa.MarkovRegression(y[:split], k_regimes=2, exog=X[:split],
                                 trend="n", switching_variance=True)
res_tr = mod_tr.fit(search_reps=25, maxiter=500)
assert res_tr.mle_retvals["converged"]

mod_all = sm.tsa.MarkovRegression(y, k_regimes=2, exog=X,
                                  trend="n", switching_variance=True)
res_oos = mod_all.filter(res_tr.params)      # causal, parameters frozen at the split
```

The filtered probability at $t$ then depends only on $y_{1:t}$ and a $\hat\theta$ estimated
strictly before the block — the real-time information set. Running the filter over the
whole series (rather than the out-of-sample block alone) means it reaches the boundary
already concentrated, which handles most of the steady-state burn-in; refit on a fixed
cadence, since frozen parameters go stale.

### Canonicalise the labels

Nothing ties "regime 0" in one fit to "regime 0" in the next — the likelihood is invariant
to permuting labels, and random restarts land on different permutations. A feature column
built across refits is meaningless without a fixed, data-independent reordering:

```python
order = np.argsort([res_tr.params[f"sigma2[{i}]"] for i in range(2)])   # low vol first
probs = res_oos.filtered_marginal_probabilities.iloc[:, order]
probs.columns = ["p_calm", "p_stressed"]
```

Assert the ordering is stable between adjacent refits; a flip usually means two regimes
have merged and the fit is degenerate.

## Checklist

- `switching_variance=True` unless you really mean mean-only; `trend="n"` if `exog` has a
  constant; `sm.add_constant` on `exog_tvtp`.
- `search_reps` ≥ 20, returns in percent, assert convergence, read
  `expected_durations` before anything else.
- Features and evaluated forecasts use `filtered_marginal_probabilities` — or
  `predicted_marginal_probabilities` when the target at $t$ is $y_t$ itself, since the
  filtered value has already consumed $y_t$. Smoothed output is for historical narrative
  only. See [Data Leakage](../concepts/data-leakage.md).
- Estimate on the training block, `filter` with frozen parameters, canonicalise labels,
  exclude burn-in, and report decoding delay next to any accuracy figure.

## MarkovAutoregression

```python
mod = sm.tsa.MarkovAutoregression(
    y, k_regimes=2, order=4, switching_ar=False, switching_variance=True
)
```

[`MarkovAutoregression`](markov-autoregression.md) subclasses this one, adding `order`
(the autoregressive lag length) and `switching_ar`. Everything above — restarts,
probability attributes, label canonicalisation, frozen-parameter filtering — carries over
unchanged. What differs is the parameterisation: it fits Hamilton's *mean-adjusted* form,
which makes the likelihood depend on the regime path $s_{t-p:t}$ rather than on $s_t$
alone, costs $K^{p+1}$ states per step, and drops the first `order` observations.

Putting lagged $y$ into this class's `exog` instead gives the *intercept*-switching
autoregression — a different model, and a much cheaper one.

## Related

- [MarkovAutoregression](markov-autoregression.md) — the autoregressive sibling, and the mean- vs intercept-switching choice
- [Switching parameters](switching-parameters.md) — unpacking `res.params` for computation, and the model methods that take a params vector
- [statsmodels](statsmodels.md) — the library around it: Model→Results, formulas, `cov_type`, and the rest of the catalogue
- [Markov Processes](../concepts/markov-models.md) — the theory this class implements
- [Bayesian Markov Models](../concepts/bayesian-markov-models.md) — what the plug-in point estimate leaves out, and the priors that replace the awkward defaults
- [Data Leakage](../concepts/data-leakage.md) — why the smoothed defaults matter
- [Time-Series Validation](../concepts/time-series-validation.md) — the walk-forward protocol the refit cadence sits inside
- [Metric Standard Errors](../../finance/metric-standard-errors.md) — `statsmodels` for HAC-corrected inference on the resulting signal
