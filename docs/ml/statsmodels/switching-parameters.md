# Switching parameters

A fitted [`MarkovRegression`](markov-regression.md) or
[`MarkovAutoregression`](markov-autoregression.md) stores everything it estimated in one
flat vector: transition probabilities, per-regime coefficients and per-regime variances,
concatenated. `res.params` is that vector with names attached, and `res.summary()`
arranges it for reading — but neither is what you want to *compute* with.

Two things make the vector usable: `mod.parameters`, an index map from (regime, purpose)
to positions, and a set of model methods that take the raw vector and return the
quantities you would otherwise rebuild by hand.

## The vector

```python
import numpy as np
import statsmodels.api as sm

mod = sm.tsa.MarkovRegression(y, k_regimes=2, exog=X,
                              trend="n", switching_variance=True)
res = mod.fit(search_reps=25)

theta = np.asarray(res.params)   # the order fit / filter / loglike all expect
mod.param_names                  # ['p[0->0]', 'p[1->0]', 'const[0]', ..., 'sigma2[1]']
mod.k_params
```

For `MarkovRegression` the blocks run in the order transitions → `exog` (the `trend`
columns are folded in front of your design matrix) → variance. Don't hard-code offsets off
that, though: `MarkovAutoregression` appends an `autoregressive` block, and `exog_tvtp`
changes the width of the transition block.

`theta` is in **natural, constrained** units — probabilities in $[0, 1]$, variances
positive. That is the same space `res.params` reports and what `transformed=True` means
everywhere in these classes.

## `mod.parameters`

`mod.parameters` is a `MarkovSwitchingParams` instance, and indexing it returns positions
in `theta` rather than values:

| indexing | returns |
|---|---|
| `mod.parameters["regime_transition"]` | slice over the transition block |
| `mod.parameters["exog"]` | slice over all regimes' coefficients |
| `mod.parameters["variance"]` | slice over the variance block |
| `mod.parameters[0, "exog"]` | indices of regime 0's $\beta$ |
| `mod.parameters[1, "variance"]` | index of regime 1's $\sigma^2$ |
| `mod.parameters[0]` | every index belonging to regime 0 |

A string key gives a `slice`; a `(regime, purpose)` pair gives a list of indices. Unpacking
the fit into arrays you can do arithmetic with is then one comprehension per block:

```python
k = mod.k_regimes
beta   = np.array([theta[mod.parameters[i, "exog"]]        for i in range(k)])  # (k, m)
sigma2 = np.array([theta[mod.parameters[i, "variance"]][0] for i in range(k)])  # (k,)
```

!!! warning "Name lookup breaks on non-switching parameters"
    `res.params["sigma2[0]"]` works in the example above only because
    `switching_variance=True` gave each regime its own slot. Turn it off — or pass
    `switching_exog=[True, False, False]` — and several regimes *share* one position, so
    there is no per-regime name to look up; `res.summary()` drops the `[i]` suffix and
    files those parameters under a separate "Non-switching parameters" block. The index
    map returns the shared index once per regime, so the comprehensions above keep working
    unchanged. Parse the `Series` index only for display.

## Methods that take the vector

The derived quantities are already implemented as methods on the **model**, each taking a
params vector. Reimplementing them from `beta` and `sigma2` is how sign and axis-order
mistakes get in.

```python
P   = mod.regime_transition_matrix(theta)   # (k, k, 1) — or (k, k, nobs) with exog_tvtp
pi  = mod.initial_probabilities(theta)      # (k,) steady-state distribution
mu  = mod.predict_conditional(theta)        # (k, nobs) — x_t'β_i, one row per regime
llf = mod.loglike(theta)                    # scalar, no results object constructed
```

- With **time-varying transition probabilities** (`exog_tvtp`), the transition block holds
  *logit coefficients*, not probabilities. `regime_transition_matrix` is the only correct
  route to $p_{ij}$, and it needs `exog_tvtp=` passed in to evaluate them at specific
  covariates.
- `mod.initial_probabilities` is the ergodic distribution $\pi$ solving $\pi = P\pi$ under
  the default steady-state initialisation — the prior the Hamilton filter starts from.
- `predict_conditional` is the regime-conditional mean, detailed below.

!!! tip "A params argument is a frozen-parameter hook"
    Because these take `theta` and not `res`, the same calls evaluate a model at
    parameters estimated on an *earlier* sample — the walk-forward pattern in
    [Frozen parameters](frozen-parameters.md). `mod.loglike(theta)` in particular is the
    cheap way to check whether a random restart actually found a better optimum.

## `predict_conditional`

The model's deterministic part evaluated under **every regime hypothesis at every $t$**,
with no probability weighting anywhere in it:

$$
\hat y_t^{(i)} = x_t^{\top}\beta_i,
\qquad i = 0, \ldots, K-1, \qquad t = 1, \ldots, T
$$

```python
mu = mod.predict_conditional(theta)   # (k_regimes, nobs) ndarray
mu[1] - mu[0]                         # distance between the two regimes' means at each t
```

- **Signature is `(params)` and nothing else** — no `start`/`end`, no `transformed`, no
  `exog`. The vector must already be in natural units, and the result always spans the
  full in-sample period, so column $t$ is observation $t$.
- **Returns a bare ndarray**, with no pandas index attached even when `endog` had one.
- **All zeros when there is nothing to predict from.** With `trend="n"` and `exog=None`
  every $\beta_i$ is absent, so the conditional mean is $0$ in all regimes — the model is
  then pure switching variance, and all of its content sits in $\sigma^2_i$ and the
  regime probabilities.

### Relation to `res.predict`

[`res.predict`](predict.md) *is* this function plus a weighting step:

$$
\hat y_t = \sum_{i} \Pr(S_t = i \mid \cdot)\, \hat y_t^{(i)}
$$

`conditional=True` returns the rows unweighted, one column per regime over
`start`…`end`; the default collapses them under `probabilities`, whose
`"smoothed"` default conditions on the whole sample. `predict_conditional` is therefore
the one variant that cannot leak — it contains no probabilities to be smoothed, only
$\beta$.

### The likelihood's inner loop

The Hamilton filter needs the regime-conditional densities, and for a Gaussian switching
regression those are a function of exactly this quantity and the regime variance:

$$
\log f(y_t \mid S_t = i, y_{1:t-1}) =
-\frac{1}{2}\left[\log\left(2\pi\sigma_i^2\right)
+ \frac{\bigl(y_t - \hat y_t^{(i)}\bigr)^2}{\sigma_i^2}\right]
$$

So `predict_conditional` is the inner loop of `loglike`, exposed. That makes it the
starting point for regime-conditional residual diagnostics, which `res.resid` does not
give you:

```python
k = mod.k_regimes
sigma2 = np.array([theta[mod.parameters[i, "variance"]][0] for i in range(k)])
resid = np.asarray(mod.endog).squeeze() - mu       # (k, nobs)
z = resid / np.sqrt(sigma2)[:, None]               # standardised within each regime
```

Use `mod.endog`, not your original `y` — `MarkovAutoregression` trims the presample, so
the two differ in length there.

### `MarkovAutoregression`

The override returns shape $(K, \ldots, K, \text{nobs})$ with $p + 1$ regime axes instead
of $(K, \text{nobs})$, because the mean-adjusted form makes the conditional mean depend on
the whole regime path $s_{t-p:t}$:

$$
\hat y_t^{(i_0, i_1, \ldots, i_p)} = x_t^{\top}\beta_{i_0}
+ \sum_{r=1}^{p} \phi_r^{(i_0)}\left(y_{t-r} - x_{t-r}^{\top}\beta_{i_r}\right)
$$

!!! note "Axis 0 is the current regime"
    Axes run $s_t, s_{t-1}, \ldots, s_{t-p}$ left to right, and $K^{p+1}$ grows fast —
    $K = 2$, $p = 4$ is already 32 surfaces per observation. `mu[i, i, i, i, i]` is the
    never-switched path, not the model's prediction for regime $i$; the prediction weights
    all $K^{p+1}$ of them by the joint path probability.

## Round-tripping

```python
res2 = mod_all.filter(theta)              # recursions at these params, nothing estimated
res3 = mod_all.fit(start_params=theta)     # warm start, transformed=True by default
u    = mod.untransform_params(theta)       # natural → optimiser space (logit / log)
theta2 = mod.transform_params(u)           # and back
mod.start_params                           # what fit() would have begun from
```

The transform pair is only needed when you hand a vector to or from the optimiser's
unconstrained space; `transformed=False` on `fit` or `filter` says the vector you are
passing is already in it.

## Uncertainty

`res.bse`, `res.cov_params()`, `res.conf_int()`, `res.tvalues` and `res.pvalues` index in
the same order as `res.params`, so `mod.parameters` slices them too:

```python
se_sigma2 = res.bse[mod.parameters["variance"]]
```

These carry the usual caveat for switching models: a transition probability estimated near
0 or 1 — the normal case for a persistent regime — sits on the boundary of the parameter
space, where [the standard errors are not meaningful](../concepts/bayesian-markov-models.md).
Judge persistence by `res.expected_durations` instead.

## Related

- [MarkovRegression](markov-regression.md) — the class whose output this unpacks, and the constructor defaults that determine the layout
- [MarkovAutoregression](markov-autoregression.md) — the extra `autoregressive` block and the regime-path axes
- [Frozen parameters](frozen-parameters.md) — `mod.filter` / `mod.smooth`, the consumers of an extracted vector
- [statsmodels](statsmodels.md) — the Model→Results split this exploits
- [Markov Processes](../concepts/markov-models.md) — what $P$, $\pi$ and the filter are
- [Bayesian Markov Models](../concepts/bayesian-markov-models.md) — why a plug-in point estimate understates the uncertainty
