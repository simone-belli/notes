---
tags:
  - design-patterns
---

# scikit-learn Pipelines

A `Pipeline` chains preprocessing transformers and a final estimator into one
object that implements `fit`/`transform`/`predict`. It is not just convenience
plumbing — it is a **correctness guarantee** that makes the most common form of
data leakage structurally impossible.

## The cardinal sin: `scale then split`

Standardisation computes `z = (x - μ) / σ`. The whole question is *whose* `μ`
and `σ`. Fit the scaler on the full series and you have averaged in the test
period — the training features are normalised using knowledge of the future.

```python
from sklearn.preprocessing import StandardScaler

# WRONG — μ, σ computed over ALL rows, test period included
X_scaled = StandardScaler().fit_transform(X)
X_train, X_test = X_scaled[:split], X_scaled[split:]
```

The model never sees a test *label*, so this feels safe. But it trains on
features scaled with future information, and the backtest score is inflated. In a
time series this is acute: `μ` leaks the future drift, `σ` leaks the future
volatility regime.

The manual fix is **split first, fit on train only, transform the test set**:

```python
X_train, X_test = X[:split], X[split:]

scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)   # μ, σ from TRAIN only
X_test_s  = scaler.transform(X_test)         # reuse train μ, σ — no re-fit
```

Note the asymmetry — `fit_transform` on train, **`transform` only** on test. This
mirrors live trading, where at prediction time you have only the past to
standardise against. It is correct but fragile: with several steps and many
cross-validation folds, one forgotten `.transform` that is silently a
`.fit_transform` reintroduces leakage.

## Pipeline draws the fit boundary for you

```python
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge

pipe = Pipeline([
    ("scaler", StandardScaler()),
    ("model",  Ridge(alpha=1.0)),
])

pipe.fit(X_train, y_train)      # scaler.fit_transform + model.fit — TRAIN only
preds = pipe.predict(X_test)    # scaler.transform + model.predict — no re-fit
```

Each step is a `(name, estimator)` tuple; every step but the last must be a
transformer (`fit`/`transform`), the last is the final estimator (`fit`/`predict`).

- `pipe.fit` walks the steps calling **`fit_transform`** on each transformer over
  the data passed in — the scaler learns `μ, σ` **inside the fold**. `X_test` is
  never handed to `fit`, so it cannot enter the mean.
- `pipe.predict` walks the same steps calling **`transform`** (never
  `fit_transform`), applying the already-learned train statistics.

The `fit_transform`-on-train / `transform`-on-test asymmetry you had to enforce
by hand is now baked into the two methods. `predict` has no fitting path, so
leaking through the public interface is not discouraged — it is *unreachable*.

!!! note "Leakage is a boundary violation"
    A Pipeline collapses a multi-step recipe into a single estimator with one
    fit boundary. Whatever is inside sees only what you passed to `.fit`. The
    Pipeline draws the boundary; you can't cross it by accident.

## Where it pays off: cross-validation

`cross_val_score`/`GridSearchCV` clone the pipeline and call `fit` on each
training fold, `predict` on the held-out fold — so the scaler is re-fitted per
fold automatically. Doing this by hand across five folds × several steps is where
manual code reliably breaks.

```python
from sklearn.model_selection import cross_val_score, TimeSeriesSplit

scores = cross_val_score(pipe, X, y, cv=TimeSeriesSplit(n_splits=5))
```

`TimeSeriesSplit` produces expanding train windows that always precede their
validation window — never shuffle a time series, as that leaks future rows into
past folds. Pipeline handles *preprocessing* leakage; `TimeSeriesSplit` handles
*temporal* leakage.

!!! warning "Necessary, not sufficient"
    A Pipeline stops preprocessing statistics from crossing the fit boundary. It
    does **not** stop a forward-looking engineered feature or a shuffled time
    series. You need leak-proof preprocessing **and** splitting **and** features.

## Supporting machinery

- `make_pipeline(StandardScaler(), Ridge())` — terser constructor that auto-names
  steps from class names (`"standardscaler"`, `"ridge"`).
- `ColumnTransformer` — apply different transformers to different columns (scale
  numerics, one-hot encode categoricals) as one `fit`/`transform` object, with
  the same per-group leakage guarantee.
- `GridSearchCV(pipe, {"model__alpha": [0.1, 1, 10]})` — address a step's
  hyperparameter with `"stepname__param"` (double underscore). The search refits
  the whole pipeline per fold, so even the scaler is re-fit per candidate.
