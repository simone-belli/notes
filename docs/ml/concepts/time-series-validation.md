---
quiz: core
---

# Time-Series Validation

Standard k-fold cross-validation assumes rows are **independent and identically
distributed** (i.i.d.) draws — which is why shuffling is safe, even required.
Financial series break both halves: neighbouring rows are correlated, and the
distribution shifts with regime. Once i.i.d. fails, the k-fold score isn't just
noisier — it's biased *upward*, and in a domain where a real edge is 52%
accuracy, the bias is the entire result.

## How a shuffled KFold lies

`KFold(shuffle=True)` puts 2024 rows in the training set and 2019 rows in the
test set. Three distinct mechanisms, each inflating the score:

- **Look-ahead** — the model sees labelled examples from inside the test
  period's regime. Knowing "this is a high-volatility trending market" is most
  of the battle, and in deployment you don't know it yet.
- **Near-duplicate rows** — rows at `t` and `t+1` built from 20-day windows
  share 19 of 20 observations. Split them across folds and the model
  interpolates between two copies of the same point instead of generalising.
- **Overlapping labels** — a forward 5-day return makes `y_t` and `y_{t+1}`
  functions of overlapping price paths, so a training label contains the answer
  to a test question.

!!! warning "The gap between protocols *is* the leak"
    Shuffled KFold on next-day direction typically reports 0.58–0.65 accuracy;
    the same features under a chronological split report 0.50–0.52. Run both:
    the difference is a diagnostic measurement of your leak, never a result.

## Expanding-window CV

Train always precedes test; the training window grows, the validation window
slides forward.

```
fold 1: TRAIN [========]                TEST [====]
fold 2: TRAIN [=============]           TEST      [====]
fold 3: TRAIN [==================]      TEST           [====]
                                   time ──────────────────────▶
```

```python
from sklearn.model_selection import TimeSeriesSplit, cross_val_score

tscv = TimeSeriesSplit(n_splits=5, test_size=250, gap=10)
scores = cross_val_score(pipe, X, y, cv=tscv)   # X must be time-sorted
```

- `n_splits` — number of (train, test) pairs.
- `test_size` — length of each validation window; set it explicitly so folds are
  comparable (the default derives it from `n_samples // (n_splits + 1)`).
- `gap` — rows discarded between train and test. The embargo knob; see below.
- `max_train_size` — cap the training window, turning expanding into **rolling**
  CV: adapts to regime change, and equal training sizes make fold scores
  genuinely comparable.

### Why it's the floor

- **Restores the arrow of time** — no training row post-dates a test row,
  structurally rather than by discipline.
- **Mirrors deployment** — production refits on history to date and predicts
  forward; this simulates exactly that loop, repeated.
- **Exposes decay** — per-fold scores form a *time series of performance*. A
  model that died in 2021 shows as a declining sequence; a shuffled KFold
  averages that death away. Read `scores` per fold, never just `scores.mean()`.

Splitting is only half the guarantee: everything that learns — scalers,
imputers, [custom feature transformers](../scikit-learn/custom-transformers.md),
*and feature selection* — must refit inside the fold, which is what a
[Pipeline](../scikit-learn/pipelines.md) enforces. Picking the top-50 correlated
features on the full sample and cross-validating afterwards is
[feature-selection leakage](data-leakage.md), and it is theatre.

## Its limitation: the boundary is porous

`TimeSeriesSplit` guarantees `max(time(train)) < min(time(test))`. That's a
claim about **timestamps**, not about **information** — and the two come apart:

- **Labels leak forward.** With a forward 5-day return and the boundary at day
  100, `y_100` is computed from days 100–105 — i.e. from test territory. The
  last `h` training rows are contaminated by the test period.
- **Features leak backward.** A 20-day feature on the first test row is built
  from days 82–101, mostly training data. The row isn't a fresh observation, so
  the score on it is inflated.

The fixes are **purging** (drop training rows whose label horizon overlaps the
test period) and **embargo** (drop a buffer of test rows after the boundary so
feature windows don't reach back). `gap` is a crude version of both:

```python
TimeSeriesSplit(n_splits=5, gap=max(label_horizon, feature_lookback))
```

!!! tip "If you change one thing, set `gap`"
    It's crude — a fixed row count rather than per-label intervals — but one
    argument converts a known-biased protocol into a roughly honest one.

### Deeper still

- **One path.** Five chronological folds aren't five independent estimates; they
  are one history cut five times, same regimes in the same order. Fold variance
  understates uncertainty badly. **Combinatorial Purged Cross-Validation**
  (test on all combinations of `k` time blocks, purged at every internal
  boundary) reassembles many backtest paths and yields a *distribution* of
  Sharpe ratios instead of a point estimate.
- **Selection bias survives every splitter.** Try 400 configurations and report
  the best, and you get a Sharpe of 2 on pure noise. No cross-validation scheme
  fixes this — record the trial count, deflate the Sharpe ratio for it, and keep
  one final period sealed until the model is frozen. See
  [Tuning a Trading Strategy](strategy-tuning.md).

## Nested CV

Tuning and scoring on the same folds reports the noise you selected for. Nest
the [search](../scikit-learn/hyperparameter-search.md), so the number you quote
estimates the *procedure*, not one model:

```python
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit, cross_val_score

search = GridSearchCV(pipe, param_grid, cv=TimeSeriesSplit(n_splits=3))  # inner: tunes
scores = cross_val_score(search, X, y, cv=TimeSeriesSplit(n_splits=5))   # outer: scores
```

!!! note "The one-sentence version"
    A shuffled KFold answers a question nobody asked — "how well would I predict
    the past if I knew the future?" — while expanding-window CV asks the right
    question but still lets the answer seep across the boundary through
    overlapping labels and rolling features, which is what purging and embargo
    exist to stop.

## Related

- [Model Validation](model-validation.md) — the k-fold premise this note is the exception to
- [Data Leakage](data-leakage.md) — the full taxonomy; purging and embargo close two entries in it
- [Tuning a Trading Strategy](strategy-tuning.md) — pooled out-of-sample scoring and the selection channel these folds don't close
- [Running Cross-Validation](../scikit-learn/cross-validation.md) — reading per-fold results out of the loop
- [Hyperparameter Search](../scikit-learn/hyperparameter-search.md) — why `cv=5` leaks even without shuffling
- [Train/Test Splitting](../scikit-learn/splitting.md) — the splitter catalogue and stratification
- [scikit-learn Pipelines](../scikit-learn/pipelines.md) — keeping preprocessing inside the fold
- [Custom Transformers](../scikit-learn/custom-transformers.md) — causal windows and warm-up gaps
