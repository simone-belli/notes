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
at `τ=0.9` the 90th percentile. It is a modelling decision, not a tuning knob.

## Built-in `loss=` — check here first

```python
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
import numpy as np
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

## Gradient boosting takes a callable

Boosting needs only the gradient and Hessian of the loss with respect to the
prediction, so LightGBM and XGBoost accept an objective function — and their
scikit-learn wrappers keep it inside the usual Pipeline and CV machinery.

```python
def asymmetric(y_true, y_pred):
    r = y_pred - y_true
    grad = np.where(r > 0, 2 * 5.0 * r, 2 * r)
    hess = np.where(r > 0, 2 * 5.0, 2.0)
    return grad, hess

LGBMRegressor(objective=asymmetric)
```

The Hessian must be positive — leaf values divide by it. Losses with zero second
derivative (absolute error) need a constant stand-in.

!!! note "Transforming the target changes the loss silently"
    `TransformedTargetRegressor(regressor=Ridge(), func=np.log1p,
    inverse_func=np.expm1)` fits squared error on `log(y)`, which penalises
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
| Linear, novel objective | Custom estimator over `scipy.optimize` |

If you customise the loss, customise the scorer to match — otherwise you train
for one thing and select for another.

## Related

- [Running Cross-Validation](cross-validation.md) — `make_scorer`, the scorer signature, and the `neg_` convention
- [The Estimator API](estimators.md) — the `fit`/`predict` contract a custom estimator must honour
- [Custom Transformers](custom-transformers.md) — the same `BaseEstimator` conventions on the preprocessing side
- [Metric Standard Errors](../../finance/metric-standard-errors.md) — once a loss is chosen, how precisely it is measured
