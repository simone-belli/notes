# The Jensen Gap

A model trained with squared error estimates $m(x) = \mathbb{E}[y \mid x]$. Often the
quantity you actually need is $\mathbb{E}[f(y) \mid x]$: a squared return, a log
growth rate, a price recovered from a log-price. Plugging in $f(\hat m(x))$ is
biased unless $f$ is affine. For convex $f$, Jensen's inequality fixes the sign:

$$\mathbb{E}[f(y) \mid x] \;\ge\; f\big(\mathbb{E}[y \mid x]\big)$$

The **Jensen gap** $\Delta(x) = \mathbb{E}[f(y) \mid x] - f(m(x))$ depends on the
whole conditional distribution $p(y \mid x)$, not on its mean. A mean estimator
alone therefore cannot correct it. Each method below brings in the missing
distributional information, either by assumption or by estimating it.

## Which estimand?

Two different problems get called "the bias":

| You want | Gap comes from | Vanishes with more data? |
|---|---|---|
| $\mathbb{E}[f(y) \mid x]$ | noise of $y$ around $m(x)$ | no |
| $f(\mathbb{E}[y \mid x])$ | estimation error of $\hat m$ | yes |

For the second, the delta method gives
$\mathbb{E}[f(\hat m)] \approx f(m) + \tfrac12 f''(m)\operatorname{Var}(\hat m)$. You
can estimate it from bootstrap or ensemble spread, and it is usually small. The
rest of this page covers the first problem.

## Delta method: curvature × variance

A second-order Taylor expansion around $m = m(x)$ gives the following (the
linear term vanishes because $\mathbb{E}[y - m \mid x] = 0$):

$$\mathbb{E}[f(y) \mid x] \approx f(m) + \tfrac12 f''(m)\,\sigma^2(x), \qquad \sigma^2(x) = \operatorname{Var}(y \mid x)$$

- To second order the correction is **additive** and needs one extra quantity,
  $\sigma^2(x)$.
- If the errors are homoscedastic, $\sigma^2(x)$ is one constant: the mean
  squared out-of-fold residual. If they are heteroscedastic, fit a second model
  on squared residuals, or train mean and variance jointly with
  `torch.nn.GaussianNLLLoss`.
- It is poor for heavy tails, and for $f = \exp$, where every derivative matters.
  Use smearing there.

## Error models and smearing

Instead of assuming that the *bias* is additive or multiplicative, assume that
the *error* is. The bias then follows. Average $f$ over the empirical residuals
(Duan's smearing estimator, generalised to any $f$):

$$
\begin{aligned}
\text{additive: } & y = m(x) + \varepsilon, & \mathbb{E}[f(y) \mid x] &\approx \tfrac1n \textstyle\sum_i f\big(\hat m(x) + r_i\big), & r_i &= y_i - \hat m(x_i) \\
\text{multiplicative: } & y = m(x)\,\eta, & \mathbb{E}[f(y) \mid x] &\approx \tfrac1n \textstyle\sum_i f\big(\hat m(x)\,\eta_i\big), & \eta_i &= y_i / \hat m(x_i)
\end{aligned}
$$

This is distribution-free. The only assumption is that the error distribution,
on the chosen scale, does not depend on $x$.

```python
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import cross_val_predict

model = HistGradientBoostingRegressor()
oof = cross_val_predict(model, X_train, y_train, cv=5)  # honest residuals
m = model.fit(X_train, y_train).predict(X_test)

eta = y_train / oof                                     # multiplicative errors
ef = np.sqrt(m[:, None] * eta[None, :]).mean(axis=1)    # E[sqrt(y) | x]
```

The broadcast builds an `(n_test, n_train)` matrix. Subsample the residuals when
$n$ is large; a few thousand is enough.

### When the correction is a constant

The correction is a single additive or multiplicative constant exactly when $f$
maps the error structure onto itself:

| Error | $f(y)$ | Exact $\mathbb{E}[f(y) \mid x]$ | Correction |
|---|---|---|---|
| additive | $ay + b$ | $f(m)$ | none |
| additive | $e^{y}$ | $e^{m}\,\mathbb{E}[e^{\varepsilon}]$ | × constant |
| additive | $y^2$ | $m^2 + \sigma^2$ | + constant |
| multiplicative | $y^k$ | $m^k\,\mathbb{E}[\eta^k]$ | × constant |
| multiplicative | $\log y$ | $\log m + \mathbb{E}[\log \eta]$ | + constant |
| other pairs | e.g. $\sqrt{y}$, additive | depends on $m(x)$ | per prediction |

The log-target retransformation in
[Transforming the Target](../scikit-learn/target-transform.md) is the $e^{y}$ row.
Under normal log-errors, $\mathbb{E}[e^\varepsilon] = e^{\sigma^2/2}$.

!!! tip "Choosing additive vs multiplicative"
    Plot the binned standard deviation of out-of-fold residuals against the
    binned prediction. A flat spread of $y - \hat m$ means additive errors. A
    spread that grows linearly with $\hat m$ (a flat spread of $y / \hat m$)
    means multiplicative errors. If it is neither, the spread depends on $x$ and
    has to be modelled.

## Recalibrating on validation data

Skip the error model and learn the correction empirically. On held-out data, map
the plug-in to the target functional:

$$f(y_i) \approx a + f\big(\hat m(x_i)\big), \qquad f(y_i) \approx c\, f\big(\hat m(x_i)\big), \qquad f(y_i) \approx g\big(\hat m(x_i)\big)$$

- Additive: $\hat a$ is the mean of $f(y_i) - f(\hat m(x_i))$.
- Multiplicative: $\hat c = \sum_i f(y_i) / \sum_i f(\hat m(x_i))$. This
  ratio-of-means keeps the total unbiased.
- Nonparametric: fit $g$ by isotonic regression. This is the regression analogue of
  probability calibration.

```python
import numpy as np
from sklearn.isotonic import IsotonicRegression

iso = IsotonicRegression(out_of_bounds="clip").fit(oof, np.sqrt(y_train))
ef = iso.predict(m)                 # estimates E[sqrt(y) | m_hat(x)]
```

!!! warning "Recalibration only sees the mean"
    Any map $g(\hat m(x))$ estimates $\mathbb{E}[f(y) \mid \hat m(x)]$, not
    $\mathbb{E}[f(y) \mid x]$. If two inputs have the same predicted mean but
    different variances, they get the same correction, and both are wrong. Add a
    spread proxy (predicted variance, volatility, regime) as a second input when
    the variance moves independently of the level.

## Predicting the distribution

The general solution is to estimate $p(y \mid x)$ and integrate $f$ against it:

- **Parametric:** predict mean and variance (Gaussian negative log-likelihood),
  or the parameters of a Gamma or Student-t distribution. Natural Gradient
  Boosting (NGBoost) and Generalised Additive Models for Location, Scale and
  Shape (GAMLSS) do this for tabular data.
- **Quantile regression:** since $Q(U) \sim y$ for $U$ uniform, the identity
  below holds for **any** $f$. Watch for quantile crossing and for poorly
  estimated tails when $f$ amplifies them.

  $$\mathbb{E}[f(y) \mid x] = \int_0^1 f\big(Q(\tau \mid x)\big)\,d\tau \approx \frac1K \sum_{k=1}^K f\big(\hat q_{\tau_k}(x)\big), \qquad \tau_k = \frac{k - \frac12}{K}$$

- **Ensembles, Monte Carlo dropout, mixture density networks:** these are the
  options for neural models.

Smearing is the special case where $\hat p(y \mid x)$ is the empirical residual
distribution shifted or scaled to $\hat m(x)$.

## Avoiding the gap

- **Train on $f(y)$ directly.** The squared-loss minimiser is
  $\mathbb{E}[f(y) \mid x]$, so no correction is needed. The cost is one model per
  functional, and $f(y)$ may be noisier than $y$ ($y^2$ of fat-tailed returns).
- **Use a link function, not a target transform.** A log link models
  $\log \mathbb{E}[y \mid x]$, not $\mathbb{E}[\log y \mid x]$. Examples are a
  generalised linear model (GLM) or `loss="poisson"` / `"gamma"` in boosting.
- **Check whether you need a mean at all.** Quantiles commute with monotone $f$
  ($Q_{f(y)}(\tau) = f(Q_y(\tau))$), so a median or quantile prediction has no
  Jensen gap.

## Pitfalls

!!! warning "Estimate every correction out-of-fold"
    In-sample residuals of a flexible model are too small, because it has partly
    fitted the noise. That shrinks $\hat\sigma^2$, the smearing spread, and the
    recalibration correction, so every method under-corrects. Use
    `cross_val_predict` or a separate calibration split, kept in time order for
    [time series](validation/time-series-validation.md).

- **A global constant when the variance moves with $x$.** It is right on
  average and wrong in every region. Validate per bin of prediction and of any
  suspected variance driver, not only in aggregate.
- **$e^{\sigma^2/2}$ under fat tails.** It is exact only for normal log-errors.
  With heavy tails, $\mathbb{E}[e^{\varepsilon}]$ is far larger. Smearing copes
  better but is driven by the largest residuals, so inspect them.
- **Leaving the domain of $f$.** If $\hat m + r_i < 0$ under $\sqrt{\cdot}$ or
  $\log$, the additive error model is wrong for a positive target. Switch to
  multiplicative errors.

## Related

- [Transforming the Target](../scikit-learn/target-transform.md) — the log-target special case
- [Model Validation](validation/model-validation.md) — held-out data for estimating corrections
