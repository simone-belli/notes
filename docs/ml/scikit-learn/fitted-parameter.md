---
tags:
  - design-patterns
---

# Fitting a Scalar Parameter

A parametric step $\hat y = f(X, p)$ whose `fit(X, y)` *learns* the scalar $p$
from the training rows — by grid search, bounded minimisation, or root-finding.
Wrapped as an [estimator](estimators.md), the search re-runs on every
cross-validation fold, so $p$ never sees test data.

## Transformer or regressor

There is no `BaseTransformer`: a transformer is
`TransformerMixin` + `BaseEstimator`. Which mixin you want depends on what the
step outputs.

- **$f(X, \hat p)$ is the prediction of $y$** → a regressor: `RegressorMixin`,
  method `predict`, free `score` ($R^2$).
- **$f(X, \hat p)$ is a feature for a downstream model** → a *supervised
  transformer* (like `TargetEncoder`). [`Pipeline.fit(X, y)`](pipelines.md)
  calls `fit_transform(X, y)` on every intermediate step, so `fit` receives
  `y`; `transform` gets no `y` and only applies $f(X, \hat p)$.

## Parameter or hyperparameter

| | Learned parameter | Hyperparameter |
|---|---|---|
| Chosen by | minimising *training* loss in `fit` | best *validation* score across folds |
| Stored as | `self.p_` | `self.p` (`__init__` argument) |
| Searched by | your code in `fit` | [`GridSearchCV`](hyperparameter-search.md) on `step__p` |

!!! warning "Capacity parameters can't be fitted in `fit`"
    If larger (or smaller) $p$ always fits the training set better — a window
    length, a regularisation strength, a bandwidth — training loss is
    monotone in $p$ and the search runs to a bound. Tune those on held-out
    folds instead. The middle path is the `RidgeCV`/`LassoCV` pattern: an
    internal cross-validation inside `fit`, winner stored as `alpha_`.

## The objective

Every strategy minimises (or zeroes) one scalar function of a scalar:

$$
\hat p = \arg\min_{p \in [a, b]} L(p), \qquad L(p) = \ell\bigl(y,\ f(X, p)\bigr)
$$

- **Search configuration is hyperparameters** (`func`, `bounds`, `method`,
  `n_candidates`, `loss`, `random_state`); **the result is fitted state**
  (`p_`, `loss_`, plus the candidate curve for diagnostics).
- Pass `func` as a module-level function, as with `FunctionTransformer` —
  lambdas don't pickle, which breaks `joblib.dump` and `n_jobs > 1`.

## Search strategies

| Strategy | Assumes | Evaluations for precision $\varepsilon$ |
|---|---|---|
| Grid | nothing | $\propto (b-a)/\varepsilon$ |
| Random | nothing | same, with uneven coverage |
| Golden-section / Brent | unimodal $L$ | $\propto \log\bigl((b-a)/\varepsilon\bigr)$ |
| Bisection / Brent root | monotone $g$, sign change on $[a, b]$ | $\left\lceil \log_2 \frac{b-a}{\varepsilon} \right\rceil$ |

- **Grid** — globally robust; the best point is within
  $\frac{b-a}{2(n-1)}$ of the true minimiser, so each extra digit costs
  $10\times$ the evaluations.
- **Random** — in 1D strictly worse than a grid. Its advantage only appears in
  many dimensions, where a grid repeats values of the few parameters that
  matter.
- **Bounded minimisation** (`minimize_scalar(..., method="bounded")`) —
  golden-section search shrinks the bracket by $1/\varphi \approx 0.618$ per
  evaluation; Brent adds parabolic steps. The default for a smooth loss, but it
  finds *a* local minimum on a multimodal one.
- **Grid → refine** — a coarse grid picks the basin, then bounded minimisation
  between its neighbours. Robust and precise for about $n + 20$ evaluations.
- **Log-scale $p$** (rates, half-lives) — `np.geomspace` for the grid,
  `scipy.stats.loguniform` for random draws, or minimise over $\log p$.

!!! note "Bisection finds roots, not minima"
    Bisection solves $g(p) = 0$ from a sign change. It fits when the fitting
    condition is an *equation* — e.g. moment matching,
    $g(p) = \frac{1}{n}\sum_i f(x_i, p) - \bar y$. Use
    `scipy.optimize.brentq`: the same bracketing guarantee, faster
    convergence, and a `ValueError` when no root lies in the bounds. To
    *minimise* without derivatives, golden-section search is bisection's
    analogue.

## Implementation

```python
import numpy as np
from scipy.optimize import brentq, minimize_scalar
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.metrics import mean_squared_error
from sklearn.utils.validation import check_is_fitted

class FittedParamTransformer(TransformerMixin, BaseEstimator):
    def __init__(self, func, bounds=(0.0, 1.0), method="bounded",
                 n_candidates=101, loss=mean_squared_error, random_state=None):
        self.func, self.bounds, self.method = func, bounds, method   # verbatim
        self.n_candidates, self.loss = n_candidates, loss
        self.random_state = random_state

    def fit(self, X, y):
        X, y = np.asarray(X), np.asarray(y)
        lo, hi = self.bounds                      # validate here, not in __init__
        obj = lambda p: self.loss(y, self.func(X, p))
        if self.method in ("grid", "random"):
            rng = np.random.default_rng(self.random_state)
            cand = (np.linspace(lo, hi, self.n_candidates) if self.method == "grid"
                    else np.sort(rng.uniform(lo, hi, self.n_candidates)))
            self.search_loss_ = np.array([obj(p) for p in cand])
            self.search_p_ = cand
            self.p_ = cand[np.argmin(self.search_loss_)]
        elif self.method == "bounded":
            self.p_ = minimize_scalar(obj, bounds=(lo, hi), method="bounded").x
        elif self.method == "root":               # mean f(X, p) == mean y
            self.p_ = brentq(lambda p: self.func(X, p).mean() - y.mean(), lo, hi)
        else:
            raise ValueError(f"unknown method {self.method!r}")
        self.loss_ = obj(self.p_)
        self.n_features_in_ = X.shape[1]
        return self

    def transform(self, X):
        check_is_fitted(self, "p_")
        return np.asarray(self.func(np.asarray(X), self.p_)).reshape(-1, 1)
```

- `random_state` becomes a generator in `fit`, so refits and `clone`s with the
  same seed reproduce.
- `transform` returns 2D `(n_samples, 1)`, as every transformer must.
- For the regressor shape: `RegressorMixin` instead of `TransformerMixin`,
  `predict` instead of `transform`, and return the 1D array.

```python
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline

def saturation(X, p):                             # module-level → picklable
    return 1 - np.exp(-p * X[:, 0])

pipe = make_pipeline(FittedParamTransformer(saturation, bounds=(1e-3, 10.0)),
                     Ridge())
pipe.fit(X_train, y_train)                        # p_ fitted on train rows only
```

## Diagnostics

- **`p_` on a bound** — the optimum is probably outside $[a, b]$; widen it.
- **Flat `search_loss_`** — $p$ is not identified by the data, and `p_` will
  jump between folds. Check its spread across cross-validation fits.
- **Fit loss vs `scoring=`** — make `loss` match the metric you select by,
  or you train for one thing and judge by another (see
  [Custom Loss Functions](custom-loss.md)).

!!! tip "Beyond one dimension"
    For a vector $p$ the grid grows as $n^d$, so random search becomes the
    derivative-free baseline. Golden-section and bisection have no direct
    multivariate form: use `scipy.optimize.minimize` and
    `scipy.optimize.root`. The class layout stays the same, with `p_` an array.

## Related

- [Custom Transformers](custom-transformers.md) — the `fit`/`transform` contract this builds on
- [Hyperparameter Search](hyperparameter-search.md) — when $p$ should be tuned on folds instead
- [Custom Loss Functions](custom-loss.md) — the multi-parameter version over `scipy.optimize.minimize`
