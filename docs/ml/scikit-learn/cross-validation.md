# Running Cross-Validation

Both functions run **the same loop** — `cross_val_score` is a thin wrapper that
throws away everything except one array of test scores:

```python
from sklearn.model_selection import cross_val_score, cross_validate

cross_val_score(est, X, y, cv=5)                    # array of test scores
cross_validate(est, X, y, cv=5)["test_score"]       # identical
```

The question is never which is correct, but how much of the result you keep.

## What the loop does

For each `(train_idx, test_idx)` from the [splitter](splitting.md): **clone** the
estimator (an unfitted copy from `get_params()`), **fit** on the train fold,
**score** on the test fold, discard.

- **The estimator you pass in is never fitted** — cross-validation estimates
  performance, it doesn't produce a model. Call `.fit` on the full data
  separately for deployment.
- Cloning per fold is what makes a [Pipeline](pipelines.md) leak-safe: the
  scaler and imputer refit inside every fold automatically.

## cross_val_score — one number per fold

```python
scores = cross_val_score(pipe, X, y, cv=5, scoring="accuracy", n_jobs=-1)
scores.mean(), scores.std()
```

A plain 1-D array of length `n_splits`. **One metric only** — passing a list
raises. No timings, no train scores, no estimators.

!!! warning "Fold spread is not a standard error"
    Folds share training data heavily, so they aren't independent samples and
    the spread understates uncertainty. And always read the individual scores:
    `[0.85, 0.84, 0.83, 0.51]` and `[0.76, 0.76, 0.75, 0.76]` have similar means
    and completely different stories.

## cross_validate — the full result

```python
cv_results = cross_validate(
    pipe, X, y, cv=5,
    scoring=["accuracy", "roc_auc", "f1"],   # multiple metrics in one pass
    return_train_score=True,
    return_estimator=True,
)
pd.DataFrame(cv_results)
```

A dict of arrays, each of length `n_splits`:

| Key | Present when | Contents |
|---|---|---|
| `fit_time`, `score_time` | always | seconds per fold |
| `test_score` | single metric | test score per fold |
| `test_<name>` | multiple metrics | one key per metric |
| `train_score` / `train_<name>` | `return_train_score=True` | score on the fold's own training data |
| `estimator` | `return_estimator=True` | the fitted clone per fold |
| `indices` | `return_indices=True` | train/test index arrays per fold |

- **Multiple metrics are nearly free** — fitting is the expensive part, scoring
  is cheap. Three metrics in one `cross_validate` costs about the same as one;
  three `cross_val_score` calls cost triple. Pass a dict to rename:
  `{"acc": "accuracy", "mae": "neg_mean_absolute_error"}`.
- **`return_train_score`** defaults to `False`. It's a *diagnostic*, not a
  performance estimate: train ≫ test means overfitting; both low means
  underfitting; both high is healthy (or leaking).
- **`return_estimator`** exposes what was actually learned per fold:

```python
coefs = np.array([est[-1].coef_ for est in cv_results["estimator"]])
coefs.std(axis=0)      # do coefficients flip sign across folds?
```

Coefficients that swing between folds mean the score is achieved by mutually
inconsistent stories each time — instability the mean score hides.

## The scoring parameter

`scoring=None` falls back to the estimator's `.score()` — accuracy for
classifiers, R² for regressors. Prefer being explicit; the default is rarely the
metric you care about. Valid strings come from
`sklearn.metrics.get_scorer_names()`.

!!! warning "`neg_` metrics return negative numbers on purpose"
    The whole selection machinery **maximises**, so losses are negated to keep
    one universal direction. `neg_mean_squared_error` gives ≤ 0, and −11.8 beats
    −15.1. Flip the sign before reporting — and note that `sqrt(-scores.mean())`
    is the root of the mean squared error (MSE) averaged over folds, not the
    mean of the per-fold root mean squared errors (RMSE). They differ.

### Adding your own scorer

Two callables are easy to conflate, and `scoring=` wants the second:

- **Metric** — `(y_true, y_pred) -> float`; everything in `sklearn.metrics`.
- **Scorer** — `(estimator, X, y) -> float`; receives the *fitted* estimator and
  decides itself which prediction method to call.

`make_scorer` is the adapter between them:

```python
from sklearn.metrics import make_scorer, fbeta_score, recall_score

f2 = make_scorer(fbeta_score, beta=2)                      # kwargs pass through
loss = make_scorer(my_cost_fn, greater_is_better=False)    # negates for you
minority = make_scorer(recall_score, pos_label=0)          # class-dependent kwargs
```

`response_method` selects what the metric is fed — `"predict"` (default),
`"predict_proba"` for log loss and Brier score, `"decision_function"` for margin
metrics, or a list like `["decision_function", "predict_proba"]` to take
whichever the estimator offers. It supersedes the older `needs_proba` and
`needs_threshold` flags.

When the metric needs the **model itself** — sparsity, latency, a custom
threshold — skip `make_scorer` and pass a function with the scorer signature:

```python
def sparsity(estimator, X, y):
    return (estimator[-1].coef_ == 0).mean()

cross_validate(pipe, X, y, scoring={"r2": "r2", "sparsity": sparsity})
```

The dict form is the one to reach for with several metrics — it names the output
keys, which come back as `test_<name>`. Strings, adapted metrics and raw
callables can be mixed freely in one dict.

!!! warning "Don't negate twice"
    `greater_is_better=False` already flips the sign. Negating inside your
    metric as well silently inverts the ranking — you'll select the worst
    candidate while everything appears to work.

Two more sharp edges: a scorer must return a **scalar** (a per-class F1 vector
fails — pick an `average=`), and an exception raised inside one is swallowed
into `nan` by the default `error_score`, so develop new scorers with
`error_score="raise"`.

## Other arguments

- **`cv`** — an int picks `StratifiedKFold` for classifiers, `KFold` otherwise.
  Pass a splitter explicitly for anything time-ordered; see
  [Time-Series Cross-Validation](time-series-cv.md).
- **`n_jobs=-1`** — folds are embarrassingly parallel. Watch for
  oversubscription when the estimator has its own `n_jobs`.
- **`error_score=np.nan`** — the default silently turns a failing fold into
  `NaN`, so `scores.mean()` becomes `nan`. Set `error_score="raise"` to debug.

## cross_val_predict

Same loop, different output: every sample gets a prediction from the fold model
that didn't train on it (out-of-fold predictions).

```python
from sklearn.model_selection import cross_val_predict

y_pred = cross_val_predict(pipe, X, y, cv=5)
y_prob = cross_val_predict(pipe, X, y, cv=5, method="predict_proba")
```

!!! warning "Don't compute your headline metric from it"
    The predictions come from **different models**, so pooling them and scoring
    once is not a valid generalisation estimate — it differs from
    `cross_val_score(...).mean()`, badly so for metrics that aren't a plain
    average over samples (R², or Area Under the Receiver Operating
    Characteristic Curve — ROC AUC).

Use it for diagnostics — residual plots, confusion matrices, calibration curves,
finding which rows are wrong — and for **stacking**, where out-of-fold
predictions are exactly the leak-free features a meta-learner needs.

## Which to use

| Situation | Use |
|---|---|
| Quick check against a baseline | `cross_val_score` |
| More than one metric | `cross_validate` |
| Diagnosing over/underfitting | `cross_validate(return_train_score=True)` |
| Inspecting per-fold coefficients | `cross_validate(return_estimator=True)` |
| Out-of-fold predictions, stacking | `cross_val_predict` |
| Tuning hyperparameters | `GridSearchCV` / `RandomizedSearchCV` |
| Honest score *after* tuning | `cross_val_score(search, X, y, cv=outer)` — nested |

!!! tip "Default to `cross_validate`"
    Read `test_score` and you've lost nothing relative to `cross_val_score` —
    but the timings, train scores and fitted estimators are already there the
    moment a result surprises you.

## Related

- [Train/Test Splitting](splitting.md) — the `cv=` splitters this loop consumes
- [scikit-learn Pipelines](pipelines.md) — what must be inside the fold
- [The Estimator API](estimators.md) — the `fit`/`score` contract being cloned
- [Time-Series Cross-Validation](time-series-cv.md) — when the int default is wrong
