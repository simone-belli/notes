# MarkovAutoregression

`sm.tsa.MarkovAutoregression` is Hamilton's (1989) Markov-switching autoregression — an
AR($p$) whose mean, autoregressive coefficients and innovation variance depend on a latent
chain:

$$
y_t - \mu_{s_t} \;=\; \sum_{r=1}^{p} \phi_{r,s_t}\,\bigl(y_{t-r} - \mu_{s_{t-r}}\bigr)
\;+\; \varepsilon_t,
\qquad \varepsilon_t \sim \mathcal{N}(0, \sigma^2_{s_t})
$$

```python
import statsmodels.api as sm

mod = sm.tsa.MarkovAutoregression(y, k_regimes=2, order=4, switching_ar=False)
res = mod.fit(search_reps=20)
```

It subclasses [`MarkovRegression`](markov-regression.md), so the fitting path, parameter
naming, probability attributes, `expected_durations` and frozen-parameter `filter` are
identical. Read that page first; this one covers only what differs. The theory is in
[Markov Processes](../concepts/markov-models.md).

## The mean-adjusted form

Note the subscripts on the right-hand side above: $\mu_{s_{t-r}}$, not $\mu_{s_t}$. Each
lag's deviation is measured against the mean in force *at that lag*. This is Krolzig's
**MSM** (switching mean) specification, and it is a modelling choice, not a detail.

The alternative is **MSI** (switching intercept):

$$
y_t \;=\; \nu_{s_t} + \sum_{r=1}^{p} \phi_r\, y_{t-r} + \varepsilon_t
$$

- **MSM** — the level jumps to $\mu_k$ the moment the chain switches.
- **MSI** — the long-run mean is $\nu_k / (1 - \sum_r \phi_r)$ and the level drifts toward
  it at the speed the AR polynomial allows.

Abrupt shift versus slow drift are different claims about the world, and the fit will not
tell you which you meant.

!!! tip "`MarkovRegression` gives you the MSI form"
    In the MSI equation $y_t$ depends on the chain only through $s_t$ — exactly the
    conditional independence `MarkovRegression` needs. So
    `sm.tsa.MarkovRegression(y, k_regimes=2, exog=lagged_y)` *is* the intercept-switching
    autoregression, at $K$ states per step instead of $K^{p+1}$.

## Cost: the $K^{p+1}$ state space

Because $\mu_{s_{t-1}}, \dots, \mu_{s_{t-p}}$ enter the conditional mean, the density of
$y_t$ depends on the whole **path** $(s_t, \dots, s_{t-p})$:

| $K$ | $p$ | configurations |
|---|---|---|
| 2 | 4 | 32 |
| 2 | 8 | 512 |
| 2 | 12 | 4096 |
| 3 | 4 | 243 |

The class filters over that expanded state and uses Kim's (1994) collapsing step to keep
the smoother tractable, but per-observation cost still grows geometrically in `order`.
Monthly data with `order=12` is impractical.

!!! warning "`switching_ar=False` does not shrink the state space"
    It cuts the parameter count — one set of $\phi$ rather than $K$ sets — which helps
    identification a lot. But the path dependence comes from $\mu_{s_{t-r}}$ in the
    mean-adjustment and survives regardless. Only the MSI form removes it.

## Constructor

```python
MarkovAutoregression(endog, k_regimes, order, trend="c", exog=None, exog_tvtp=None,
                     switching_ar=True, switching_trend=True, switching_exog=False,
                     switching_variance=False, dates=None, freq=None, missing="none")
```

- **`order`** — the AR lag length $p$, required. The most expensive choice in the call.
- **`switching_ar`** — defaults `True`; accepts a list of booleans, one per lag.
  Hamilton's gross national product (GNP) model sets it `False`: the business cycle
  changes the growth rate, not the propagation mechanism.
- **`switching_exog`** — defaults **`False`**, the opposite of `MarkovRegression`. Easy to
  miss when porting a specification between the two.
- **`switching_variance`** — defaults `False`, the same trap as in `MarkovRegression`.
- **`exog`** — mean-adjusted the same way, so a regressor's lagged values enter the
  recursion. Not the usual "add a column" semantics.

## Presample observations

The likelihood is **conditional on the first `order` observations**, so `res.nobs` is
`len(y) - order` and the probability frames start at `y.index[order]`:

```python
probs = res.filtered_marginal_probabilities    # index starts at y.index[order]
feature = probs[1].reindex(y.index)            # align on the index, never on position
```

Aligning with `.values` shifts the regime signal by $p$ periods — a leak-shaped bug that
looks like excellent predictive power.

!!! warning "AIC across different `order` values is not comparable"
    Different `order` means a different effective sample, so the log-likelihoods measure
    different things. Fit every candidate on the same truncated sample — `y[max_order:]` —
    before comparing `aic` or `bic`.

## Parameters

With `trend="c"`, `k_regimes=2`, `order=4`, `switching_ar=False`:

```
p[0->0]   p[1->0]       # K(K-1) free transition parameters
const[0]  const[1]      # the regime MEANS, not intercepts
ar.L1 ... ar.L4         # no [regime] suffix — shared across regimes
sigma2                  # one variance unless switching_variance=True
```

!!! warning "`const[k]` is the mean, not an intercept"
    In a plain AR you recover the mean as $\text{const} / (1 - \sum_r \phi_r)$. Under the
    mean-adjusted parameterisation `const[k]` **is** $\mu_k$ already. Dividing is a common
    and badly wrong reading of the output.

That display is `summary()`'s; the underlying vector gains an `autoregressive` block after
the variance, so slice it through the
[`mod.parameters` index map](switching-parameters.md) rather than by position or name.

`switching_ar=True` adds `[0]` / `[1]` suffixes to the AR names. A single regime's AR
polynomial may legitimately be explosive — regime-switching models of bubbles rely on it,
and the overall process can still be stationary — but an explosive regime whose expected
duration is near 1 is a degenerate fit, not a bubble.

## Forecasting

These are not state space results: there is no `forecast(h)` or `get_forecast` with
intervals, and no [`append` / `extend` / `apply`](frozen-parameters.md). More
fundamentally, the $h$-step predictive density is
[a mixture](../concepts/bayesian-markov-models.md) over $K^h$ regime paths, so it is
multimodal whenever the regimes separate and a point forecast can sit in a trough
between two modes.

Simulate instead: draw regime paths from $\hat{P}$ starting at
$\Pr(S_T \mid y_{1:T})$, propagate the recursion with sampled innovations, and read
quantiles off the paths.

## When to reach for it

- **Yes** — real persistence in the conditional mean plus a discrete shift in it: GDP
  growth, industrial production, unemployment, inflation. Hamilton's canonical fit is US
  GNP growth with $K = 2$, $p = 4$, `switching_ar=False`.
- **No** — daily asset returns. The conditional mean is noise; you want switching variance
  and no AR terms, which is
  `sm.tsa.MarkovRegression(y, k_regimes=2, switching_variance=True)` and far cheaper.
- **Unavailable** — multivariate regime switching (MS-VAR); `statsmodels` has no such
  class.

Random restarts, reading `expected_durations` first, canonicalising labels across refits,
and preferring filtered over smoothed probabilities all carry over unchanged from
[MarkovRegression](markov-regression.md).

## Related

- [MarkovRegression](markov-regression.md) — the shared API, in detail
- [Switching parameters](switching-parameters.md) — unpacking the parameter vector for computation
- [Markov Processes](../concepts/markov-models.md) — the theory this class implements
- [Frozen parameters](frozen-parameters.md) — `mod.filter(params)` for the walk-forward loop
- [Data Leakage](../concepts/data-leakage.md) — why the presample offset matters
