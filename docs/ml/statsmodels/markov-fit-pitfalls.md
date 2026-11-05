# Markov-switching fit pitfalls

Things to check before trusting a Hamilton-style
[`MarkovRegression`](markov-regression.md) fit:

- **`em_iter`** controls how much of the fit runs as Expectation–Maximisation (EM) before
  the gradient optimiser takes over. Set it too low and the optimiser can fail to converge.
- **Collinear `exog`** leaves the per-regime regressions without a unique solution, and
  that gets worse inside a regime that has few observations.
- **Overlapping windows in `endog`** add serial correlation that the model's likelihood
  assumes is absent. The Markov chain then absorbs it as fake regimes.
- **Outliers and fat tails** can turn a regime into a bin for a few extreme points, or
  shrink its variance towards zero around a single observation.
- **Structural breaks** produce a regime the chain enters once and never leaves. That is
  a change point, not a recurring state.
- **Missing values and gaps** put NaNs into the likelihood, or hide a time gap inside
  what the chain treats as a single step.

Constructor defaults, random restarts, scaling, and label switching are covered in
[MarkovRegression](markov-regression.md) and aren't repeated here.

```python
import numpy as np
import statsmodels.api as sm

mod = sm.tsa.MarkovRegression(y, k_regimes=2, exog=X, trend="n", switching_variance=True)
res = mod.fit(em_iter=50, search_reps=25, maxiter=500)
assert res.mle_retvals["converged"]
```

## `em_iter` and convergence

`fit` works in two stages. First come `em_iter` EM iterations (default 5), each run with
zero tolerance so exactly that many happen. Then
Broyden–Fletcher–Goldfarb–Shanno (BFGS) or another `method=` optimises the transformed
parameters, starting from where EM stopped, for up to `maxiter` iterations. The two
algorithms are good at different things:

| | EM (Baum–Welch) | BFGS |
|---|---|---|
| Far from the optimum | Robust: every step raises the likelihood | Can step into flat or degenerate regions |
| Near the optimum | Slow (linear convergence) | Fast (superlinear convergence) |
| Constraints | Satisfied automatically by the closed-form M-step | Enforced only through the logit and log transforms |
| Output | Point estimate only | Point estimate and Hessian, so standard errors |

The M-step for `MarkovRegression` is a weighted least-squares fit for each regime. The
weights are the smoothed regime probabilities:

$$
\hat\beta_i = \left(X^{\top} W_i X\right)^{-1} X^{\top} W_i\, y,
\qquad W_i = \operatorname{diag}\!\big(\Pr(s_t = i \mid y_{1:T})\big)
$$

Here is why the EM iterations prevent non-convergence. Started from a poor point, BFGS
works on logit-probabilities and log-variances, and it tends to fail in one of three
ways:

- It pushes a $p_{ii}$ towards 0 or 1, where the logit gradient vanishes and the
  optimiser stalls.
- It shrinks one regime's $\sigma^2_i$ towards 0 around a handful of points. The
  likelihood is unbounded there, so the search runs off to $-\infty$ in log-variance.
- It stops after `maxiter` iterations, still crawling along a ridge.

More EM iterations move the starting point into the basin of a proper maximum, and BFGS
then only has to finish the job. When `converged` is `False`:

- Raise `em_iter` to somewhere between 50 and 200 before raising `maxiter`. EM
  iterations are cheap.
- Or run EM to convergence yourself, then hand its estimate to the optimiser:

```python
params_em = mod.fit_em(maxiter=500, tolerance=1e-8, return_params=True)
res = mod.fit(start_params=params_em, em_iter=0, maxiter=1000)
```

!!! warning "What `em_iter` cannot do"
    - **It does not escape local optima.** EM is deterministic and climbs to the
      nearest mode. Only random restarts (`search_reps`) search across modes. Each
      restart runs `search_iter` EM steps, which is a separate setting from `em_iter`.
    - **It is skipped with `exog_tvtp`.** With time-varying transition probabilities
      (TVTP), `fit` silently drops the EM stage, because the transition update has no
      closed form. TVTP fits therefore lean entirely on `search_reps`, sensible
      `start_params`, and well-scaled data.

## Collinear exogenous variables

When the columns of `exog` are nearly linearly dependent, $X^{\top} W_i X$ is close to
singular. This hurts more than it would in ordinary least squares (OLS), because each
regime only gets part of the sample:

$$
n_i^{\text{eff}} = \sum_{t=1}^{T} \Pr(s_t = i \mid y_{1:T})
$$

A design that is fine on the full sample can be singular inside a regime that covers 10%
of it. The symptoms:

- Large regime coefficients with opposite signs that cancel out ($\hat\beta_{1,0} \approx
  -\hat\beta_{2,0}$), and that change from one restart to the next.
- A likelihood that is flat in some direction, which gives a singular Hessian, `NaN` or
  huge standard errors, and a "covariance could not be estimated" warning.
- Unstable regimes. The optimiser can explain the data by shuffling weight between
  collinear columns instead of separating regimes, so the regime labels and their meaning
  change between refits.

Common causes:

- A constant in `exog` together with the default `trend="c"`.
- A full set of dummy variables plus a constant.
- Several rolling features over nested windows, such as 5-day and 20-day realised
  volatility, which share most of their inputs.
- Several lags of one persistent feature.

To diagnose it, check the design's condition number and the Variance Inflation Factors
(VIFs). Then repeat the condition-number check on each regime's weighted design:

```python
from statsmodels.stats.outliers_influence import variance_inflation_factor

Xs = (X - X.mean()) / X.std()
np.linalg.cond(Xs)                                          # > 30 is a red flag
[variance_inflation_factor(Xs.values, j) for j in range(Xs.shape[1])]   # > 10 is a red flag

w = res.smoothed_marginal_probabilities.iloc[:, 0].values   # regime 0's weights
np.linalg.cond(Xs.values.T @ (w[:, None] * Xs.values))      # regime 0's weighted Gram matrix
```

Fixes, from least to most invasive:

- Drop or merge redundant columns. Use one volatility feature, not three.
- Standardise the columns. This also improves the BFGS scaling.
- Keep the coefficients that don't need to switch fixed across regimes with
  `switching_exog=[True, False, ...]`. That removes $K-1$ parameters per column and lets
  the full sample identify them.
- Orthogonalise the columns, for example with principal component analysis (PCA) or by
  regressing one feature on another and keeping the residual.

## Overlapping windows in the endogenous series

`MarkovRegression` assumes the observations are **conditionally independent given the
regime**: $\varepsilon_t$ is independent and identically distributed (i.i.d.) within a
regime. An overlapping target breaks this by construction. Take an $h$-period forward
return sampled every period:

$$
y_t = \sum_{k=0}^{h-1} r_{t+k}
\quad\Longrightarrow\quad
\operatorname{Corr}(y_t, y_{t+j}) = 1 - \frac{j}{h}, \qquad 0 \le j < h
$$

This holds even when the $r_t$ are i.i.d. Neighbouring values share $h-1$ of their $h$
terms, which makes $y_t$ a moving average of order $h-1$ (MA($h-1$)).

The model has only one source of serial dependence, the Markov chain, so the chain soaks
up the autocorrelation:

- **Spurious regimes.** A run of high $y_t$ is one positive shock counted $h$ times.
  The fit labels it a "high regime", and with enough overlap it finds regimes even in
  pure noise.
- **Inflated persistence.** The estimated $p_{ii}$ rise and `expected_durations` stretch
  towards at least $h$, whatever the true regime dynamics are.
- **Overconfident inference.** The likelihood treats $T$ observations as independent
  when they carry roughly $T/h$ worth of information. Standard errors shrink by about
  $\sqrt{h}$, and the Akaike and Bayesian information criteria (AIC, BIC) penalise too
  weakly, so they favour too many regimes.
- **Overreacting filter.** Every $y_t$ updates the Hamilton filter as fresh evidence, so
  the filtered probabilities settle on a regime too quickly and too firmly.

!!! warning "`cov_type="robust"` does not fix this"
    The robust option is a sandwich estimator for a misspecified density. It is not a
    heteroskedasticity- and autocorrelation-consistent (HAC) correction, and Markov
    switching models have no built-in HAC option. The fix belongs in the data, not the
    covariance estimate.

Fixes:

- **Model the one-period series.** Fit the regimes on $r_t$, then derive the $h$-period
  behaviour from the fitted chain. This is the cleanest option.
- **Subsample without overlap.** Use `y.iloc[::h]`, which leaves $T/h$ observations.
  Fitting each of the $h$ starting offsets separately shows how much the estimates
  depend on where the sampling starts.
- If you must keep the overlap, treat the point estimates as descriptive and ignore the
  standard errors, the likelihood-ratio and information-criterion comparisons, and any
  expected duration shorter than about $h$.

!!! tip "Sanity check: fit pure noise"
    Simulate i.i.d. returns, apply the same rolling window, and fit the same model. If
    the noise fit also produces confident, persistent regimes, the overlap is creating
    the regimes in your real data too.

    ```python
    import pandas as pd

    r = pd.Series(np.random.default_rng(0).standard_normal(2000))
    y_fake = r.rolling(20).sum().dropna()
    res_fake = sm.tsa.MarkovRegression(y_fake, k_regimes=2, switching_variance=True).fit(search_reps=10)
    res_fake.expected_durations
    ```

Overlapping windows in `exog` don't break the independence assumption, which concerns
$\varepsilon_t$. They do create the collinearity described above. Overlapping labels also
leak information across a train/test split; see
[Time-Series Validation](../concepts/validation/time-series-validation.md).

## Outliers and fat tails

Each regime's density is Gaussian. Returns have fatter tails than that, and the cheapest
way for the model to explain a crash day is to give it a regime of its own. Two failure
modes follow:

- **Outlier regime.** One regime covers a handful of extreme points. Its variance is
  huge, its expected duration is close to 1, and its average probability is tiny. It
  describes the tails of the distribution, not a persistent state.
- **Variance collapse.** A regime settles on one or two observations and its variance
  heads to zero. The likelihood is unbounded as $\sigma^2_i \to 0$, so this "maximum" is
  degenerate even when `converged` is `True`.

Before interpreting the regimes, check how much of the sample each one covers, how long
each one lasts, and how small the smallest variance is:

```python
probs = res.smoothed_marginal_probabilities
probs.mean()                    # share of the sample in each regime; < 2-3% is suspicious
res.expected_durations          # close to 1 means a noise or outlier regime
res.params.filter(like="sigma2")   # compare the smallest with the sample variance of y
```

Fixes:

- Winsorise the series, for example with `y.clip(y.quantile(0.001), y.quantile(0.999))`.
- Put known one-off events in `exog` as a dummy column that does not switch.
- Restart from a different `start_params` and compare `llf`. A degenerate fit usually
  sits at a suspiciously high likelihood.
- Accept that the regime is a jump regime and stop calling it "crisis". That name is
  only earned if the regime persists.

## Structural breaks and few transitions

A one-time change in level or volatility, such as a policy shift or a change in market
microstructure, fits perfectly as a regime with $p_{ii} \approx 1$ that the chain enters
once. The fit looks excellent and predicts nothing, because the regime never recurs.

The transition probabilities can only be estimated from switches that actually happen.
With $N_{ij}$ observed switches from $i$ to $j$, the estimate of $p_{ij}$ rests on those
few events, whatever the sample length $T$ is:

$$
\hat p_{ij} \approx \frac{N_{ij}}{\sum_k N_{ik}}
$$

Count the switches before trusting $\hat p_{ij}$ or `expected_durations`. Smoothed
probabilities are fine for this check, since it only looks back at the history:

```python
states = res.smoothed_marginal_probabilities.values.argmax(axis=1)
n_switches = int((np.diff(states) != 0).sum())   # a handful means p_ij is barely identified
```

- One switch means a break. Model it with a dummy variable or a split sample instead of
  a regime.
- Detrend or difference trending series first. A level that drifts slowly gets carved
  into "low" and "high" regimes that are really just early and late parts of the sample.
- Use a longer history with several complete cycles if you want regimes that recur.

## Missing values and gaps

The Hamilton filter needs a value at every step:

- A NaN in `endog` or `exog` turns the log-likelihood into NaN, so the optimiser fails
  or returns NaN parameters. Drop or fill missing values explicitly before building the
  model.
- Dropping rows makes the chain step straight across the gap. A 10-day hole then counts
  as a single transition, which biases $p_{ii}$ upwards in the regime that was active
  around the gap.
- Mixing frequencies does the same thing, for example daily data whose holidays are
  spaced irregularly, or data that switches from weekly to daily. $p_{ij}$ is a
  per-step probability, so every step must cover the same length of time.

!!! note "Smoothed probabilities are for diagnostics only"
    Every check on this page uses smoothed probabilities, and that is fine because they
    are diagnosing the fit. Features and forecasts still need the filtered or predicted
    probabilities. See [MarkovRegression](markov-regression.md).

## Related

- [MarkovRegression](markov-regression.md) — constructor defaults, `search_reps`, the results object
- [MarkovAutoregression](markov-autoregression.md) — where genuine autoregressive dependence belongs
- [Markov Processes](../concepts/sequence-models/markov-models.md) — EM, the Hamilton filter, and conditional independence
- [statsmodels](statsmodels.md) — the condition-number footnote in OLS summaries
- [Metric Standard Errors](../../finance/metric-standard-errors.md) — HAC corrections for overlapping returns outside the switching model
- [Purged Cross-Validation](../concepts/validation/purged-cross-validation.md) — splitting when labels overlap in time
