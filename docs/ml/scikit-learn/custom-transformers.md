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

## At a fold boundary

Everything above is enough for a transformer whose `fit` only needs the rows it
is given. A rolling or recursive feature needs more: its first rows depend on
data that the fold slice cut away. See
[Fold-Safe Transformers](fold-safe-transformers.md) for causal windows, burn-in
buffers, burn-in vs embargo, and what breaks under non-contiguous splits.

## Related

- [Pipelines](pipelines.md) — the fit boundary a transformer has to live inside
- [Cross-Validation](cross-validation.md) — what re-fits the transformer per fold
