# Train/Test Splitting

Hold out data the model never trains on, to estimate how it generalises — see
[Model Validation](../concepts/model-validation.md) for why the estimate needs a
protocol at all. The cardinal rule: **split first, then fit everything (scalers,
imputers, model) on the training part only** — see [Pipelines](pipelines.md) for
why this must be structural.

## train_test_split

```python
from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,        # 20% held out (or train_size=...)
    random_state=42,      # reproducible split
    shuffle=True,         # default; shuffles before splitting
    stratify=y,           # keep class proportions (classification)
)
```

- Returns the four splits in a fixed order: `X_train, X_test, y_train, y_test`.
- `stratify=y` — preserve each class's proportion in both splits; standard for
  imbalanced classification.
- Accepts any number of equal-length arrays (`X, y, weights, …`) and splits them
  consistently.

!!! warning "`shuffle=True` leaks the future in a time series"
    The default shuffle scatters future rows into the training set — a look-ahead
    leak. For time-ordered data, never shuffle: split by time so the test period
    strictly follows the train period.

## Time-series split (no shuffle)

```python
# simple chronological hold-out
split = int(len(X) * 0.8)
X_train, X_test = X[:split], X[split:]
y_train, y_test = y[:split], y[split:]
```

## Cross-validation splitters

For repeated splits, pass a splitter as `cv=` to
[`cross_val_score`](cross-validation.md)/`GridSearchCV`:

```python
from sklearn.model_selection import KFold, StratifiedKFold, TimeSeriesSplit, cross_val_score

cross_val_score(model, X, y, cv=KFold(n_splits=5, shuffle=True, random_state=42))
cross_val_score(model, X, y, cv=StratifiedKFold(n_splits=5))   # preserves class balance
cross_val_score(model, X, y, cv=TimeSeriesSplit(n_splits=5))   # expanding window
```

- `KFold` — `k` equal folds; each is the test set once. `shuffle=True` only if
  rows are exchangeable (not a time series).
- `StratifiedKFold` — `KFold` that preserves class proportions per fold;
  classification default.
- `TimeSeriesSplit` — expanding train window that always **precedes** its
  validation window; the time-series-safe replacement for `KFold`. See
  [Time-Series Validation](../concepts/time-series-validation.md) for its
  parameters and for the leak it *doesn't* fix.

!!! note "Splitting is the other half of leak-proofing"
    A [Pipeline](pipelines.md) stops preprocessing statistics from crossing the
    fit boundary; the splitter decides where that boundary is. Shuffle a time
    series and no Pipeline can save you — leak-safe preprocessing **and** a
    leak-safe split.
