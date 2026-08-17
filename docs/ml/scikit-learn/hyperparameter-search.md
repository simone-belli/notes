---
tags:
  - performance
---

# Hyperparameter Search

`fit` learns *parameters* (coefficients, split thresholds). It never learns
*hyperparameters* — `alpha`, `max_depth`, `learning_rate` are constructor
arguments fixed before `fit` runs. Choosing them means trying candidates and
comparing cross-validated scores, which is the loop these two classes package:

```python
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV
```

!!! note "A searcher is itself an estimator"
    `GridSearchCV(pipe, grid)` has `fit`/`predict`/`score`/`get_params` — a
    *meta-estimator* whose `fit` runs many `fit`s and keeps the winner. That is
    why it can be nested inside another `cross_val_score`, or dropped into a
    [Pipeline](pipelines.md) like any other step.

## The interface

```python
search = GridSearchCV(
    estimator=pipe,
    param_grid={"model__alpha": [0.01, 0.1, 1.0, 10.0]},
    scoring="neg_mean_absolute_error",
    cv=TimeSeriesSplit(n_splits=5, gap=10),
    n_jobs=-1,
    refit=True,
)
search.fit(X, y)
```

Everything except the grid and `refit` is inherited from
[`cross_validate`](cross-validation.md) and means the same thing — `scoring`,
`cv`, `n_jobs`, `error_score`, `return_train_score`.

### Addressing parameters

Grid keys are strings passed to `set_params`; `__` descends one level into a
composite estimator.

```python
{
    "model__alpha": [0.1, 1, 10],                        # step "model"
    "prep__num__imputer__strategy": ["mean", "median"],  # nested three deep
}
```

`pipe.get_params().keys()` lists every legal key. Two non-obvious uses:

- **Values are arbitrary objects**, so a whole step is searchable:
  `{"model": [Ridge(), RandomForestRegressor()]}` compares model families in one
  search, and `{"prep__scaler": [StandardScaler(), "passthrough"]}` toggles a step.
- **A list of dicts is a union of grids**, for parameters that only co-occur:

```python
[{"svc__kernel": ["linear"], "svc__C": [0.1, 1, 10]},
 {"svc__kernel": ["rbf"], "svc__C": [0.1, 1, 10], "svc__gamma": [1e-3, 1e-4]}]
# 3 + 6 = 9 candidates, none of them illegal
```

### refit

`refit=True` (default) retrains the winner on **all** the data and stores it as
`best_estimator_`; the searcher then delegates `predict` to it.

- `refit=False` — no `best_estimator_`, `predict` raises; results only.
- Multi-metric scoring makes `True` ambiguous — name the deciding metric,
  `refit="roc_auc"`.
- A **callable** `cv_results_ -> best_index_` implements rules like "simplest
  model within one standard error of the best".

### Reading results

```python
search.best_params_, search.best_score_, search.best_estimator_, search.best_index_
pd.DataFrame(search.cv_results_).sort_values("rank_test_score")
```

`cv_results_` holds one row per candidate: `params`, a `param_<name>` column per
searched parameter, `split0_test_score`…, `mean_test_score`, `std_test_score`,
`rank_test_score`, `mean_fit_time`. The shape of that surface says more than the
winner does:

- **Flat** — the hyperparameter doesn't matter; stop tuning it.
- **Winner at the grid edge** — the optimum is outside; extend and re-run.
- **Spiky** — you are fitting fold noise.
- **Per-split columns** — with a time-series splitter they are time-ordered, so
  they read as a decay curve.

!!! warning "`best_score_` is not the performance of `best_estimator_`"
    `best_score_` is the *maximum* over many noisy estimates, so it is biased
    upward; `best_estimator_` is a different model, trained on more data. Neither
    is an honest out-of-sample estimate of the other.

## Why the exhaustive grid doesn't scale

Grid search evaluates the Cartesian product: `fits = ∏ len(values_i) × n_splits`.
The runtime is multiplicative in the *number* of hyperparameters.

| Hyperparameters | 5 values each | × 5 folds | At 2 s/fit, 8 cores |
|---|---|---|---|
| 2 | 25 | 125 | 31 s |
| 4 | 625 | 3,125 | 13 min |
| 6 | 15,625 | 78,125 | 5.4 hours |
| 8 | 390,625 | 1,953,125 | 5.6 days |

Gradient boosting has at least six hyperparameters worth touching, and five
values each is a *coarse* grid. Worse, the budget isn't yours to set: it's
dictated by the grid, so halving the runtime means deleting an axis.

The subtler objection (Bergstra & Bengio, 2012) applies even at fixed budget. Nine
evaluations as a 3×3 grid test **3 distinct values** of each hyperparameter; nine
random draws test **9 distinct values** of each. Since only one or two
hyperparameters usually move the score — and which ones varies by dataset — the
grid squanders most of its budget resolving axes that turn out to be flat.

Random search also comes with a budget guarantee. Each draw lands in the top 5%
of the space with probability 0.05, so `n` draws hit it with probability
`1 − 0.95ⁿ`: 30 draws → 79%, **60 draws → 95%**. That number is independent of
the number of hyperparameters.

## RandomizedSearchCV

```python
from scipy.stats import loguniform, randint, uniform

search = RandomizedSearchCV(
    pipe,
    param_distributions={
        "model__learning_rate": loguniform(1e-3, 1e-1),
        "model__max_depth": randint(3, 12),            # 3..11
        "model__subsample": uniform(0.6, 0.4),         # loc, scale → [0.6, 1.0]
        "model__max_features": ["sqrt", "log2", None], # list → uniform choice
    },
    n_iter=60,                 # the budget knob
    cv=TimeSeriesSplit(n_splits=5),
    random_state=42,
    n_jobs=-1,
)
```

- Values are a list (sampled uniformly) or anything with `rvs` — any
  `scipy.stats` distribution.
- `n_iter × n_splits` fits, decoupled from the dimensionality: you set it from
  the time you have.
- `random_state` is required for reproducibility. If every distribution is a
  list, sampling is without replacement and `n_iter` is clipped to the grid size.

!!! tip "`loguniform` for anything spanning orders of magnitude"
    `uniform(1e-5, 1e-1)` puts 90% of its draws above 0.01 and effectively never
    samples 1e-4 — three of the four decades go unexplored. `loguniform` spreads
    draws evenly across exponents, which is what you meant. (The grid equivalent
    is `np.logspace(-5, -1, 5)`, not five evenly spaced values.)

**Grid still wins** for 1–2 parameters, genuinely small discrete spaces, or when
you want the full surface to plot. The standard workflow is both: randomized
search to find the region, then a tight grid inside it.

## With the time-series splitter

- **`cv=5` is silently wrong.** It means `KFold(shuffle=False)`, so the earliest
  fold trains on everything *after* it. No shuffling removes the obvious leak and
  leaves the fundamental one. Pass `TimeSeriesSplit` explicitly, with `gap` — a
  model tuned under a leaking protocol is tuned to exploit the leak. See
  [Time-Series Validation](../concepts/time-series-validation.md).
- **Fold cost isn't uniform** — the expanding window makes later folds far more
  expensive, badly so for algorithms superlinear in `n`. `max_train_size` bounds
  it; `Pipeline(steps, memory="./cache")` caches fitted transformers so
  preprocessing isn't recomputed for every candidate that leaves it unchanged.
- **Refitting on all data is right; quoting `best_score_` is not.** Deployment
  wants the freshest regime. But the max over 60 noisy estimates is biased upward
  by roughly the noise scale — an apparent 55% accuracy on a 52%-edge signal is
  consistent with a true 50%. In finance this is **backtest overfitting**.

Nest the searcher to get an honest number — legitimate precisely because it is an
estimator:

```python
search = RandomizedSearchCV(pipe, dists, n_iter=40, cv=TimeSeriesSplit(n_splits=3))
scores = cross_val_score(search, X, y, cv=TimeSeriesSplit(n_splits=5))   # 5×40×3 fits
```

!!! note "What nested CV gives you"
    `scores.mean()` estimates how well the *tuning procedure* generalises — the
    number to report. It does not give you a model: each outer fold picked its
    own hyperparameters. Run one final search on everything for deployment.

## Faster searchers

**Successive halving** starts many candidates on a small resource, keeps the top
fraction, doubles the resource, repeats:

```python
from sklearn.experimental import enable_halving_search_cv   # noqa: F401 — mandatory
from sklearn.model_selection import HalvingRandomSearchCV

search = HalvingRandomSearchCV(pipe, dists, factor=3, resource="n_samples")
```

The enabling import must come first — these are still experimental. Same result
attributes, typically 3–10× faster, at the risk of cutting a candidate that was
slow to prove itself. Beyond scikit-learn, **Optuna** (Tree-structured Parzen
Estimator plus pruning) is the practical standard for large spaces. Sophistication
runs grid → random → halving → Bayesian; how often each is the right call runs
random ≫ everything else.

## Recipe

1. Search a [Pipeline](pipelines.md), never a bare estimator.
2. Explicit splitter, explicit `scoring`.
3. `RandomizedSearchCV`, `n_iter=60`, `loguniform` for scale parameters,
   `random_state` set.
4. Read `cv_results_` as a DataFrame — flat axes, edge winners, per-fold decay.
5. Optionally refine with a small grid around the winner.
6. Don't quote `best_score_`; nest, or keep a final period sealed.
7. Record how many configurations you tried — that count deflates everything you
   report.

## Related

- [Running Cross-Validation](cross-validation.md) — the inner loop and the `scoring` argument
- [Train/Test Splitting](splitting.md) — the splitters passed as `cv=`
- [scikit-learn Pipelines](pipelines.md) — what `step__param` addresses
- [The Estimator API](estimators.md) — the contract that makes nesting work
- [Time-Series Validation](../concepts/time-series-validation.md) — why `cv=5` leaks
- [Model Validation](../concepts/model-validation.md) — selection bias on the maximum
