# The Estimator API

**scikit-learn** (`sklearn`) is Python's standard library for *classical* machine
learning — linear/logistic regression, SVMs, trees, forests, gradient boosting,
k-means, PCA — built on NumPy and SciPy. Its defining feature is not any one
algorithm but that **every model wears the same interface**: learn it once and
you can swap one estimator for another by changing a single line.

## The estimator

An **estimator** is any object that learns from data. You construct it with
hyperparameters, then teach it with `.fit`.

```python
from sklearn.linear_model import Ridge

model = Ridge(alpha=1.0)     # construct with hyperparameters (no data yet)
model.fit(X_train, y_train)  # learn parameters from data; returns self
```

Two kinds of attribute live on an estimator, kept apart by a naming convention:

- **Hyperparameters** — what *you* set, passed to `__init__`, stored under the
  same name (`model.alpha`). Set before fitting.
- **Learned attributes** — what `.fit` learns from data, stored with a
  **trailing underscore** (`model.coef_`, `scaler.mean_`, `kmeans.cluster_centers_`).
  They exist only after fitting; touching one before raises `NotFittedError`.

!!! tip "If it ends in `_`, the data taught it"
    The trailing-underscore convention is universal across the library. It is
    the quickest way to tell a knob you turned from a value the model learned.

## The four verbs

Estimators specialise by which methods they implement:

- **`fit(X, y)`** — learn from data. Every estimator has it; returns `self` so
  calls chain. Unsupervised estimators (`KMeans`, `PCA`, `StandardScaler`) take
  just `X`.
- **`predict(X)`** — one output per row. **Predictors** (classifiers, regressors)
  have it.
- **`transform(X)`** — a modified `X`. **Transformers** (scalers, encoders,
  `PCA`, feature selectors) have it.
- **`score(X, y)`** — a default metric (accuracy for classifiers, R² for
  regressors); used by cross-validation.

| Kind        | Learns then… | Examples |
|-------------|--------------|----------|
| Predictor   | `predict`    | `Ridge`, `LogisticRegression`, `RandomForestClassifier` |
| Transformer | `transform`  | `StandardScaler`, `OneHotEncoder`, `PCA`, `SelectKBest` |

Transformers also offer **`fit_transform(X)`** — fit then transform in one call.
Keeping `fit` and `transform` as *separate* methods is what lets you fit on the
training data and merely apply to the test data — the basis of leakage-safe
evaluation with [Pipelines](pipelines.md).

## The consistency payoff

Because the interface is fixed, swapping models is a one-line change:

```python
from sklearn.ensemble import RandomForestRegressor

model = RandomForestRegressor(n_estimators=200)   # same .fit / .predict / .score
model.fit(X_train, y_train)
model.predict(X_test)
```

The same uniformity lets *meta*-tools accept any estimator without knowing which
one it is:

- [`cross_val_score(est, X, y, cv=...)`](cross-validation.md) clones and
  fits/scores across folds.
- [`GridSearchCV(est, param_grid)`](hyperparameter-search.md) is *itself* an estimator (`fit`/`predict`) that
  searches hyperparameters by cross-validation; nested params use double
  underscore, `"model__alpha"`.
- `Pipeline([...])` chains transformers and a final predictor into one estimator.

!!! note "The whole library in one contract"
    Construct with hyperparameters → `fit` to learn (results land in
    `trailing_underscore_` attributes) → `predict` (predictors) or `transform`
    (transformers). Because the contract never varies, everything composes.

## Orientation

- **Import paths group by family**: `sklearn.linear_model`, `sklearn.ensemble`,
  `sklearn.svm`, `sklearn.preprocessing`, `sklearn.model_selection`,
  `sklearn.metrics`, `sklearn.cluster`, `sklearn.decomposition`.
- **`X` is 2-D** (`n_samples × n_features`); **`y` is 1-D** for single-target
  supervised learning.
- **Metrics** beyond `score` live in `sklearn.metrics` (`accuracy_score`,
  `mean_squared_error`, `roc_auc_score`).
- **`random_state`** — pass an int to any stochastic estimator (tree ensembles,
  k-means, shuffled splits) for reproducibility.
