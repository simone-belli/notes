# Imputation

Real feature matrices have holes — a dropped tick, an unreported volume — showing
up as `NaN`. Almost every scikit-learn estimator (scalers, linear models) **raises
on `NaN`**, so you must fill the gaps first. An **imputer** does the filling, and
it is a transformer (`fit`/`transform`), so it slots into the same leak-safe
machinery as a scaler.

## SimpleImputer

```python
from sklearn.impute import SimpleImputer

imp = SimpleImputer(strategy="median")
imp.fit(X_train)                     # learns one fill value per column, from TRAIN
X_test_filled = imp.transform(X_test)   # fills test holes with TRAIN medians
```

Replaces each missing value with a single per-column statistic chosen by `strategy`:

- `"mean"` — column mean; fine for roughly symmetric features.
- `"median"` — **robust to outliers/fat tails**; the safer default for financial
  magnitudes (returns, volumes).
- `"most_frequent"` — modal value; the choice for **categoricals** before one-hot.
- `"constant"` — a fixed `fill_value` (e.g. `0`, or `"missing"` as an explicit
  category).

Learned fills live in `imp.statistics_`. `missing_values` (default `np.nan`) can
target another sentinel (e.g. a legacy `-999`).

!!! note "An imputer learns, so it can leak"
    A median is a statistic over rows. Compute it over the whole dataset and you
    fold the test period into the value you fill training rows with — the same
    [scale-then-split leak](pipelines.md) in disguise. `fit` learns on the
    training fold; `transform` applies. Never re-fit on test.

## Put it in a Pipeline

Because the fill is learned, imputation has the train/test discipline of scaling
— chain it **before** the scaler (which also can't handle `NaN`) and model:

```python
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge

pipe = Pipeline([
    ("impute", SimpleImputer(strategy="median")),
    ("scale",  StandardScaler()),
    ("model",  Ridge()),
])
```

With mixed column types, put the imputer inside a
[`ColumnTransformer`](column-transformer.md) branch — median for numerics,
most-frequent for categoricals.

## Richer imputers

`SimpleImputer` uses only the column itself; these use the other features:

- `KNNImputer` — fills from the **k-nearest neighbours** (rows closest on the
  non-missing features); sensitive to scaling, slower.
- `IterativeImputer` — models each incomplete feature as a **regression on the
  others**, cycled to convergence (scikit-learn's Multivariate Imputation by
  Chained Equations, MICE). Experimental — needs an opt-in import:

  ```python
  from sklearn.experimental import enable_iterative_imputer  # noqa: F401
  from sklearn.impute import IterativeImputer
  ```

Both are transformers with the same contract — same Pipeline slot, same leakage
discipline.

!!! tip "Impute *and* flag when absence is meaningful"
    If the *fact* of missingness carries signal (a feed going dark in stressed
    markets), `SimpleImputer(..., add_indicator=True)` appends a 0/1 column per
    feature marking which entries were imputed — a plausible value goes in, and
    the missingness pattern is preserved for the model.
