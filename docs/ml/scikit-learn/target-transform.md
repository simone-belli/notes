---
tags:
  - design-patterns
---

# Transforming the Target

A [`Pipeline`](pipelines.md) only transforms `X` — `y` is threaded through every
step untouched, and a transformer's `transform` returns one array, so no step can
modify the target. Taking $\log y$ is therefore not a Pipeline step but a
**wrapper around the whole regressor**: `TransformedTargetRegressor`.

## TransformedTargetRegressor

```python
import numpy as np
from sklearn.compose import TransformedTargetRegressor
from sklearn.linear_model import Ridge

ttr = TransformedTargetRegressor(
    regressor=Ridge(alpha=1.0),
    func=np.log1p,
    inverse_func=np.expm1,
)
ttr.fit(X_train, y_train)      # Ridge sees log1p(y_train)
preds = ttr.predict(X_test)    # expm1 applied — back on y's own scale
```

With $g$ the inner regressor and $f$ the target transform:

$$\hat y(x) = f^{-1}\big(g(x)\big), \qquad g \ \text{fitted on}\ \{(x_i,\, f(y_i))\}$$

- `fit(X, y)` clones `regressor` and fits it on `func(y)`; the fitted inner model
  is `ttr.regressor_`.
- `predict(X)` applies `inverse_func`, so **predictions and scores are always on
  the original scale** — an $R^2$ or MAE stays comparable with an untransformed
  model.
- `check_inverse=True` (default) round-trips a subsample and warns if
  `inverse_func(func(y)) != y` — it catches `np.log`/`np.exp` on a `y` containing
  zeros, or a mismatched `log`/`expm1` pair.
- Regression only. Label-side work for classifiers belongs to `LabelEncoder`.

## Two ways to specify the transform

Mutually exclusive — passing both raises.

| | What it is | Learns from `y`? |
|---|---|---|
| `func` / `inverse_func` | stateless callable pair — `np.log1p`/`np.expm1`, `np.sqrt`/`np.square` | no |
| `transformer=` | an object with `fit`/`transform`/`inverse_transform` | yes, re-fit per fold |

```python
from sklearn.compose import TransformedTargetRegressor
from sklearn.preprocessing import PowerTransformer
from sklearn.linear_model import Ridge

TransformedTargetRegressor(
    regressor=Ridge(),
    transformer=PowerTransformer(method="yeo-johnson"),  # λ fitted per fold
)
```

`StandardScaler`, `PowerTransformer` (Box-Cox / Yeo-Johnson $\lambda$ by maximum
likelihood) and `QuantileTransformer(output_distribution="normal")` all fit here;
`y` is reshaped to a 2-D column internally, so `X`-side transformers work
unmodified.

!!! tip "This is the leak-safe place to do it"
    A `PowerTransformer` fitted on the full `y` before splitting leaks the test
    period's distribution into training. Inside the wrapper it is re-fitted on
    each training fold, exactly like an `X`-side step inside a Pipeline — see
    [data leakage](../concepts/validation/data-leakage.md).

## Composing with a Pipeline

Put the wrapper **outermost** — the feature pipeline is what gets wrapped.

```python
import numpy as np
from sklearn.compose import TransformedTargetRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.model_selection import GridSearchCV

inner = Pipeline([("scale", StandardScaler()), ("model", Ridge())])
model = TransformedTargetRegressor(
    regressor=inner, func=np.log1p, inverse_func=np.expm1
)

GridSearchCV(model, {"regressor__model__alpha": [0.1, 1, 10]})
```

The result is an ordinary estimator, so it drops into `cross_val_score`,
[`GridSearchCV`](hyperparameter-search.md), or another Pipeline's final slot —
[parameter paths](hyperparameter-search.md) just gain a `regressor__` hop.

## Why fit on log(y)

Least squares minimises *absolute* squared error. In log space it minimises
something close to *relative* error, since for small residuals

$$\log y - \log \hat y = \log\!\left(\frac{y}{\hat y}\right) \approx \frac{y - \hat y}{\hat y}$$

- Right for a strictly positive, right-skewed, multiplicative target — prices,
  volumes, counts, durations.
- Pulls a long right tail towards symmetry, which squared-error losses handle far
  better.
- Flattens residuals that fan out with the level (heteroscedasticity).

## The bias it introduces

The inverse transform does not preserve the loss. If the inner model estimates
the conditional mean of $\log y$ then, $\exp$ being convex, Jensen's inequality
gives

$$\mathbb{E}[y \mid x] = \mathbb{E}\big[e^{\log y} \mid x\big] > e^{\mathbb{E}[\log y \mid x]} = \hat y(x)$$

so `predict` is biased **low** as an estimate of the mean. Under
$\log y \mid x \sim \mathcal{N}(\mu(x), \sigma^2)$ you get back the conditional
*median*, short by a constant factor:

$$\mathbb{E}[y \mid x] = e^{\mu(x) + \sigma^2/2} = \hat y(x)\, e^{\hat\sigma^2/2}$$

Options, crudest last-resort first:

- Accept it — the median is often what you wanted.
- Multiply by $e^{\hat\sigma^2/2}$, with $\hat\sigma^2$ the log-space residual
  variance.
- Duan's smearing estimator — multiply by $\frac{1}{n}\sum_i e^{r_i}$ over the
  log-space residuals $r_i$; distribution-free.
- Use a log **link** instead of transforming `y`: `PoissonRegressor`,
  `GammaRegressor`, `HistGradientBoostingRegressor(loss="poisson")`. A link keeps
  the loss on the original scale, so there is no bias to undo.

!!! warning "The manual version breaks cross-validation"
    `model.fit(X, np.log1p(y))` then `np.expm1(model.predict(X_test))` is fine
    for a single fit. Pass `np.log1p(y)` to `cross_val_score` and every score
    comes back in log space — not comparable with the untransformed model, and
    not in the target's units. See [custom loss](custom-loss.md) for why a target
    transform is a silent change of objective.

## Related

- [Pipelines](pipelines.md) — the `X`-side fit boundary this wraps
- [Custom Loss Functions](custom-loss.md) — transforming `y` as an implicit loss change
- [Custom Transformers](custom-transformers.md) — `FunctionTransformer`, the `X`-side analogue
