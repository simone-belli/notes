# Custom Loss Functions

The loss is what `fit` minimises; the [scorer](cross-validation.md#the-scoring-parameter)
is what selection maximises. They are separate knobs, and only the first changes
the fitted model.

!!! warning "`scoring=` does not change how anything is fitted"
    Passing `make_scorer(my_cost)` to `GridSearchCV` fits every candidate with
    its own built-in loss and merely picks a different winner. That is useful,
    but it is not training against your objective — don't report it as one.

Choosing a loss is choosing *which functional of the conditional distribution*
you estimate: squared error targets the mean, absolute error the median, pinball
at $\tau = 0.9$ the 90th percentile. It is a modelling decision, not a tuning knob.

## Built-in `loss=` — check here first

```python
import numpy as np
from sklearn.linear_model import SGDRegressor
from sklearn.ensemble import HistGradientBoostingRegressor

SGDRegressor(loss="huber", epsilon=1.35)                      # outlier-robust
SGDRegressor(loss="epsilon_insensitive")                      # SVR dead zone
HistGradientBoostingRegressor(loss="absolute_error")          # median
HistGradientBoostingRegressor(loss="quantile", quantile=0.9)  # pinball
HistGradientBoostingRegressor(loss="poisson")                 # counts
```

- `SGDClassifier(loss=...)` — `hinge` (linear SVM), `log_loss`,
  `modified_huber`, `perceptron`.
- Some estimators *are* the loss choice: `HuberRegressor`, `QuantileRegressor`,
  `RANSACRegressor`.

## `sample_weight` — reweight without rewriting

Multiplies each term of the existing loss. Cost-sensitive learning, imbalance,
and recency weighting all live here.

```python
w = np.where(y > threshold, 5.0, 1.0)
model.fit(X, y, sample_weight=w)

pipe.fit(X, y, **{"model__sample_weight": w})   # step prefix inside a Pipeline
```

It scales the per-observation penalty; it cannot change its *shape*.

## A custom estimator over `scipy.optimize`

scikit-learn does not accept a callable `loss=` — its solvers are hand-derived
(coordinate descent, Cholesky, LBFGS with analytic gradients), so there is
nowhere to hand an arbitrary Python function. Wrap the optimiser in the
[estimator API](estimators.md) instead:

```python
from scipy.optimize import minimize
from sklearn.base import BaseEstimator, RegressorMixin

class AsymmetricLinear(BaseEstimator, RegressorMixin):
    def __init__(self, penalty=5.0):
        self.penalty = penalty              # store unchanged

    def _objective(self, w, X, y):
        r = y - X @ w                       # r < 0 → over-predicted
        return np.mean(np.where(r < 0, self.penalty * r**2, r**2))

    def fit(self, X, y):
        self.coef_ = minimize(self._objective, np.zeros(X.shape[1]),
                              args=(X, y)).x
        return self

    def predict(self, X):
        return X @ self.coef_
```

`__init__` storing its arguments untouched is what makes `get_params`/`clone`
work, so this searches and pipelines like any built-in. The same two conventions
govern [custom transformers](custom-transformers.md).

- Put a `StandardScaler` ahead of it in the Pipeline — badly scaled columns make
  quasi-Newton solvers crawl.
- Warm-start `x0` from the least-squares solution rather than zeros.
- If `not res.success`, raise `sklearn.exceptions.ConvergenceWarning` as the
  built-ins do.

## Derivatives: what to hand `minimize`

All the choice is in what `minimize` receives. With parameters $\theta$, the
objective is

$$
L(\theta) = \frac{1}{n}\sum_{i=1}^{n} \ell\big(y_i,\, f(x_i;\theta)\big) + \alpha\,\lVert\theta\rVert_2^2
$$

### No gradient — finite differences

Passing only the function, as above, makes `minimize` run
Broyden–Fletcher–Goldfarb–Shanno (BFGS) on a finite-difference gradient:

$$
\frac{\partial L}{\partial \theta_j} \approx \frac{L(\theta + h\,e_j) - L(\theta)}{h}, \qquad h \approx \sqrt{\varepsilon_{\text{mach}}}
$$

- Costs $p + 1$ full passes over the data per gradient, for $p$ parameters.
- Loses about half the digits; "Desired error not necessarily achieved due to
  precision loss" is the usual symptom — check `res.x`, it is often fine.
- Fine for a smooth loss with tens of parameters.

### Derivative-free methods — non-smooth losses

Kinks and jumps (`np.where`, absolute value, step-shaped costs) make a
finite-difference gradient meaningless. Use a method that never asks for one:

```python
minimize(obj, x0, args=(X, y), method="Nelder-Mead")   # simplex, no bounds
minimize(obj, x0, args=(X, y), method="Powell", bounds=bnds)

from scipy.optimize import differential_evolution
differential_evolution(obj, bounds=bnds, args=(X, y))   # global, needs bounds
```

These degrade fast beyond ~20 parameters. Past that, either **smooth** the loss
(pseudo-Huber $\delta^2\big(\sqrt{1 + (r/\delta)^2} - 1\big)$ for $\lvert r\rvert$)
and use gradients, or **reformulate** it — absolute and quantile loss are
linear programs, which `QuantileRegressor(solver="highs")` already solves.

### Analytic gradient — `jac=True`

Return `(value, gradient)` from one function so the residuals are computed once.
For the asymmetric loss above, with $c_i = k$ where $r_i < 0$ and $1$ otherwise:

$$
L(w) = \frac{1}{n}\sum_i c_i r_i^2, \qquad \nabla_w L = -\frac{2}{n} X^\top (c \odot r)
$$

```python
def _loss_grad(self, w, X, y):
    r = y - X @ w
    c = np.where(r < 0, self.penalty, 1.0)
    return np.mean(c * r**2), -2 * X.T @ (c * r) / len(y)

res = minimize(self._loss_grad, w0, args=(X, y), jac=True, method="L-BFGS-B")
```

One pass per iteration, exact to machine precision, and Limited-memory BFGS
(L-BFGS-B) handles thousands of parameters. A `hess=` for `"trust-exact"` or
`"Newton-CG"` is possible but rarely pays off.

!!! warning "Check every hand-written gradient"
    A wrong gradient doesn't crash — the fit just stops early or converges to
    the wrong point. `from scipy.optimize import check_grad`, then
    `check_grad(loss, grad, w0, X, y)` returns the norm of the gap to a
    finite-difference estimate; it should be tiny relative to the gradient.

### Automatic differentiation — write the loss, get the gradient

```python
import jax
import jax.numpy as jnp
jax.config.update("jax_enable_x64", True)   # L-BFGS needs float64

def loss(w, X, y, k):
    r = y - X @ w
    return jnp.mean(jnp.where(r < 0, k * r**2, r**2))

vg = jax.jit(jax.value_and_grad(loss))

def fun(w, *args):
    v, g = vg(w, *args)
    return float(v), np.asarray(g)

minimize(fun, w0, args=(X, y, 5.0), jac=True, method="L-BFGS-B")
```

Analytic-gradient speed with none of the derivation. At a kink autodiff returns
*a* subgradient, so a non-smooth loss stays non-smooth.

## Gradient boosting takes a callable

Boosting needs only the gradient and Hessian of the loss with respect to the
prediction, so LightGBM and XGBoost accept an objective function — and their
scikit-learn wrappers keep it inside the usual Pipeline and CV machinery.

```python
from lightgbm import LGBMRegressor

def asymmetric(y_true, y_pred):
    r = y_pred - y_true
    grad = np.where(r > 0, 2 * 5.0 * r, 2 * r)
    hess = np.where(r > 0, 2 * 5.0, 2.0)
    return grad, hess

LGBMRegressor(objective=asymmetric)
```

The Hessian must be positive — leaf values divide by it. Losses with zero second
derivative (absolute error) need a constant stand-in, which turns each Newton
step into a plain gradient step. There is no derivative-free mode here, but
`jax.vmap(jax.grad(...))` can produce `grad` and `hess` instead of deriving them.

!!! note "Transforming the target changes the loss silently"
    [`TransformedTargetRegressor(regressor=Ridge(), func=np.log1p,
    inverse_func=np.expm1)`](target-transform.md) fits squared error on `log(y)`, which penalises
    *proportional* error — a relative-error objective from a least-squares
    solver. Deliberate use is excellent; accidental use is a surprise, and
    predictions come back biased low because the mean of a log is not the log
    of the mean.

## Which route

| Situation | Route |
|---|---|
| A built-in `loss=` fits | Use it — almost always the answer |
| Reweight, not reshape | `sample_weight` / `class_weight` |
| Only need the right model *selected* | `scoring=` + `make_scorer` |
| Trees, novel objective | LightGBM/XGBoost `objective=` callable |
| Linear, novel smooth objective | Custom estimator + gradient (`jac=True` or JAX) + L-BFGS-B |
| Novel non-smooth objective, few params | Custom estimator + Nelder-Mead / Powell |
| Novel non-smooth objective, many params | Smooth surrogate, or a linear-program solver |

If you customise the loss, customise the scorer to match — otherwise you train
for one thing and select for another.

## Related

- [Running Cross-Validation](cross-validation.md) — `make_scorer`, the scorer signature, and the `neg_` convention
- [The Estimator API](estimators.md) — the `fit`/`predict` contract a custom estimator must honour
- [Custom Transformers](custom-transformers.md) — the same `BaseEstimator` conventions on the preprocessing side
- [Fitting a Scalar Parameter](fitted-parameter.md) — the one-parameter case: grid, bounded minimisation, root-finding
- [Metric Standard Errors](../../finance/metric-standard-errors.md) — once a loss is chosen, how precisely it is measured
