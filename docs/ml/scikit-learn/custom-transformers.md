---
tags:
  - design-patterns
---

# Custom Transformers

Your real features — [rolling](../../data/pandas/transforming/windows.md) stats, regime tags,
cross-asset interactions — don't exist in scikit-learn; you write them. Compute
them in pandas over the full frame before splitting and you
[leak](../concepts/data-leakage.md): any feature built from a cross-row statistic
(mean, quantile, fitted boundary) folds the test period into training. Fix: wrap the feature as a **transformer** so it lives
inside the [Pipeline](pipelines.md) and is recomputed per fold, leak-free.

## The fit/transform contract

```python
from sklearn.base import BaseEstimator, TransformerMixin
```

- `BaseEstimator` — `get_params`/`set_params`, `repr`, and compatibility with
  `clone`/`GridSearchCV`/`step__param` addressing.
- `TransformerMixin` — supplies `fit_transform` for free.

Two rules keep it well-behaved:

- **`__init__` stores hyperparameters verbatim** — `self.window = window`, same
  name, no logic/validation (`clone` reconstructs via `get_params`).
- **Anything learned from data goes in `fit`, under a `trailing_underscore_`**;
  `fit` returns `self`. `transform` only *applies* — it learns nothing new.

### Stateless feature — `fit` is a no-op

```python
import pandas as pd

class RollingMean(BaseEstimator, TransformerMixin):
    def __init__(self, window=20):
        self.window = window            # hyperparameter → tunable "rollingmean__window"

    def fit(self, X, y=None):
        return self                     # nothing learned

    def transform(self, X):
        return pd.DataFrame(X).rolling(self.window).mean().to_numpy()  # backward only
```

### Stateful feature — the statistic is learned on train

```python
class VolRegime(BaseEstimator, TransformerMixin):
    def __init__(self, quantile=0.8):
        self.quantile = quantile

    def fit(self, X, y=None):
        self.threshold_ = pd.Series(X.ravel()).quantile(self.quantile)  # TRAIN only
        return self

    def transform(self, X):
        return (X > self.threshold_).astype(int)                        # apply learned
```

`threshold_` is learned on the training fold and applied unchanged to the test
fold. In a Pipeline each fold re-learns its own — computing the quantile over the
full series would leak the future.

!!! note "Feature engineering is preprocessing"
    Any feature built from a cross-row statistic is a *learned* thing — it must
    live inside the Pipeline's fit boundary (in `fit`), not in a pandas step
    before the split. Only truly stateless reshapes may skip `fit`.

## FunctionTransformer — stateless shortcut

```python
import numpy as np
from sklearn.preprocessing import FunctionTransformer

log1p = FunctionTransformer(np.log1p)   # wraps a plain function; learns nothing
```

Use it when there's nothing to learn; write a `BaseEstimator` class the moment
`fit` must remember something.

## Rolling windows at fold boundaries

!!! warning "Two traps, easy to conflate"
    **(1) Keep windows causal.** A backward-looking window (uses `… t-1, t`)
    doesn't leak; a *centered/forward* window (`center=True`, `shift(-k)`, any
    future-anchored value) puts tomorrow into today's feature — a look-ahead leak
    wherever it sits.
    **(2) Warm-up gap ≠ leak.** Transforming a fold in isolation gives a causal
    rolling feature no access to the tail of the preceding data, so its first
    `window - 1` rows come out `NaN`/truncated — pessimistic, not leaky.

One criterion settles both: a transform leaks **iff some output row depends on
an input row that comes after it in time**. Direction is everything — prepending
*earlier* rows is what production does, so it is causal, not leaky. See
[Time-Series Validation](../concepts/time-series-validation.md) for why the
boundary stays porous in both directions.

## Carrying a burn-in buffer

An exponentially weighted moving average (EWMA) is the case that hurts. It's a
recursion, `s_t = α·x_t + (1-α)·s_{t-1}`, so restarting it at the first test row
yields plausible-looking wrong numbers rather than the `NaN`s a `rolling` window
would show. Fix: remember the training block's tail in `fit`, prepend it in
`transform`.

```python
class EWMA(BaseEstimator, TransformerMixin):
    def __init__(self, halflife=10, burn_in=None):
        self.halflife = halflife
        self.burn_in = burn_in

    def _k(self):
        return self.burn_in or int(np.ceil(10 * self.halflife))

    def fit(self, X, y=None):
        X = pd.DataFrame(X)
        self.buffer_ = X.iloc[-self._k():].copy()      # this fold's train tail
        return self

    def transform(self, X):
        X = pd.DataFrame(X)
        prior = self.buffer_[self.buffer_.index < X.index[0]]   # earlier rows only
        out = pd.concat([prior, X]).ewm(halflife=self.halflife, adjust=False).mean()
        return out.iloc[len(prior):]                   # trim back to len(X)
```

- **Filter the buffer by index.** `fit_transform` is `fit(X).transform(X)` —
  without `index < X.index[0]`, transforming the *training* block would prepend
  X's own tail to its front. The filter empties the buffer there and fills it on
  the test block, so one comparison makes both paths correct.
- **Trim back to `len(X)`.** A transformer must return the row count it received;
  extra rows silently misalign everything downstream against `y`.
- **Size from the hyperparameter.** Pre-buffer influence decays as
  `2^(-k/halflife)`, so 10 half-lives (≈ 3.5 `span`) leaves ~0.1%. Deriving
  `burn_in` from `halflife` keeps it right when a
  [search](hyperparameter-search.md) tries a longer one.

!!! note "The buffer is a fitted attribute"
    `self.buffer_` is as legitimate as `self.mean_` — it just isn't *learned*.
    Statistically stateless (nothing estimated from the data) doesn't excuse you
    from `fit`: the contract is that whatever `transform` needs beyond `X` comes
    from `fit`. Obeying it buys `clone`, so every fold refits its own buffer.

### Carrying state instead of rows

With `adjust=False` the recursion is Markovian, so one number per column
replaces the whole buffer. pandas has no initial-value argument, but the first
output equals the first input — prepend a single row holding the stored state
and the continuation is *exact*, not approximate:

```python
    def fit(self, X, y=None):
        X = pd.DataFrame(X)
        self.state_ = X.ewm(halflife=self.halflife, adjust=False).mean().iloc[-1]
        self.state_at_ = X.index[-1]
        return self
```

This needs `adjust=False`; pandas' default `adjust=True` normalises by a running
weight sum and needs both a numerator and denominator state, so a single-value
seed is wrong. Carry rows instead whenever the feature has no finite sufficient
statistic — rolling windows, diffs, ranks.

## Burn-in vs embargo

Not the same knob, and easy to conflate. Burn-in fixes a *feature* that is wrong
at the fold start (an artifact of the split); purging and embargo fix a *score*
that is optimistic (overlapping labels, near-duplicate rows) by dropping rows
from training and scoring. Use both: the gap rows' raw `X` is legitimate burn-in
— those prices are known in production — you just never train or score on them.

Fold 1 has no prior data at all. Reserve a **global burn-in prefix** so every
fold is comparable, sized for the longest half-life in the grid:

```python
X_model, y_model = X.iloc[k:], y.iloc[k:]   # first k rows are buffer-only
```

## Keeping the index alive

Buffer logic keyed on the index needs a DataFrame; a numpy array raises
`TypeError: '<' not supported between instances of 'Timestamp' and 'int'`.
scikit-learn steps emit numpy by default, so put the transformer **first** in
the Pipeline, or run upstream steps under `set_output(transform="pandas")` —
which requires each custom transformer to define `get_feature_names_out`, as
`TransformerMixin` attaches `set_output` only to subclasses that have it.

!!! tip "Don't build this unless you're tuning"
    A causal EWMA precomputed over the full series *doesn't leak* — no output row
    depends on a later input row. If the half-life is fixed, compute it in pandas
    and skip all of the above. The buffer earns its keep by making the in-Pipeline
    result numerically equal to that precompute, so `halflife` can become a tunable
    `ewma__halflife` without a warm-up penalty at every boundary.
