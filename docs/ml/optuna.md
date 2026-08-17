---
tags:
  - performance
---

# Optuna

A framework-agnostic library for hyperparameter optimisation (HPO). Where
[`RandomizedSearchCV`](scikit-learn/hyperparameter-search.md) is *memoryless* —
draw 60 has learned nothing from draws 1–59 — Optuna models the trials it has
already paid for and samples where that model expects improvement, and kills
losing evaluations early to reclaim their budget.

```python
import optuna

def objective(trial: optuna.Trial) -> float:
    lr = trial.suggest_float("learning_rate", 1e-3, 0.3, log=True)
    depth = trial.suggest_int("max_depth", 2, 12)
    return evaluate(lr, depth)          # any float you want minimised

study = optuna.create_study(direction="minimize")
study.optimize(objective, n_trials=100)
study.best_params, study.best_value
```

## Define-by-run

The one design idea that makes it different. scikit-learn is **define-and-run**:
you hand the searcher a static dict describing the space. Optuna is
**define-by-run**: you hand it a function, and the space comes into existence as
a side effect of executing it. `trial.suggest_float(...)` is not a declaration —
it is a call returning an actual float, chosen now from all history so far.

!!! note "You get the host language back"
    `if`, `for`, and function calls work *inside* the search space. Same shift as
    TensorFlow 1 → PyTorch for computation graphs.

```python
def objective(trial):
    name = trial.suggest_categorical("model", ["ridge", "gbdt"])
    if name == "ridge":
        model = Ridge(alpha=trial.suggest_float("alpha", 1e-3, 1e3, log=True))
    else:
        model = HistGradientBoostingRegressor(
            max_depth=trial.suggest_int("max_depth", 2, 12))
    n_lags = trial.suggest_int("n_lags", 1, 20)     # later params depend on it
```

`alpha` exists only in trials where `model == "ridge"`. The `param_grid` union of
dicts expresses that awkwardly; a parameter *count* that depends on a sampled
value it cannot express at all.

The cost: the space is unknown until the function runs, so nothing validates your
ranges up front and a typo in a parameter **name** silently creates a new
parameter instead of raising.

## The suggest API

```python
trial.suggest_float("lr", 1e-5, 1e-1, log=True)     # log=True is not the default
trial.suggest_float("frac", 0.1, 1.0, step=0.05)    # discretised
trial.suggest_int("n_units", 16, 1024, log=True)
trial.suggest_int("layers", 2, 10, step=2)          # 2, 4, 6, 8, 10
trial.suggest_categorical("kernel", ["linear", "rbf"])
```

- `log=True` for anything spanning orders of magnitude — otherwise 90% of draws
  land in the top decade, exactly as with `uniform` vs `loguniform`.
- `suggest_categorical` takes only `None`/`bool`/`int`/`float`/`str`, so the
  `{"model": [Ridge(), RandomForest()]}` trick becomes a string plus an `if`.
  Choices are treated as **unordered**, so express ordered sets like
  `[16, 32, 64]` as `suggest_int(..., log=True)` and let the sampler interpolate.
- No `neg_` convention: set `direction="minimize"` and return the error itself.

## Samplers

**TPE** (Tree-structured Parzen Estimator) is the default. It inverts classic
Bayesian optimisation: rather than modelling `p(y | x)` with a Gaussian process,
it splits completed trials into good and bad at a quantile, fits a kernel density
to each — `l(x)` and `g(x)` — and picks the candidate maximising `l(x)/g(x)`.
That ratio is monotone in Expected Improvement, so you get EI-driven search with
no surrogate over `y` and no kernel matrix to invert — which is why it handles
20+ dimensions and conditional spaces where a Gaussian process struggles.
"Tree-structured" is the conditional part: each parameter's density uses only the
trials where it was actually suggested.

```python
optuna.samplers.TPESampler(
    seed=42,               # reproducibility needs this, not a global seed
    n_startup_trials=10,   # random draws before the model engages
    multivariate=True,     # joint density — models interactions
    constant_liar=True,    # distributed runs: stops workers proposing the same point
)
```

The default TPE is **univariate**: one independent density per parameter, so it
cannot represent "high learning rate works, but only with shallow trees".
`multivariate=True` is worth switching on for gradient-boosting spaces.

| Sampler | Use when |
|---|---|
| `TPESampler` | default — tens to thousands of trials, mixed/conditional spaces |
| `RandomSampler` | the honest baseline; also right under ~20 trials |
| `GPSampler` | expensive objective, small budget, low-dimensional, continuous |
| `CmaEsSampler` | continuous, >100 trials, no categoricals |
| `NSGAIISampler` | multi-objective (default when you pass `directions=[...]`) |
| `GridSampler` | you genuinely want exhaustive |

## Pruning

Sampling picks *where* to evaluate; pruning decides *how long*. For any objective
with a learning curve — boosting rounds, epochs, folds — you often know early
that a configuration will lose.

```python
for epoch in range(100):
    score = train_one_epoch()
    trial.report(score, epoch)
    if trial.should_prune():
        raise optuna.TrialPruned()      # state PRUNED, not FAIL — curve is kept
```

- **`MedianPruner`** (default) — cut if worse than the median of completed trials
  at the same step. `n_startup_trials` and `n_warmup_steps` stop it being
  trigger-happy.
- **`SuccessiveHalvingPruner`** / **`HyperbandPruner`** — the asynchronous
  cousins of `HalvingRandomSearchCV`; Hyperband hedges the "how early is too
  early" question across brackets and pairs well with TPE.
- **`WilcoxonPruner`** — for objectives that average over many instances (folds,
  assets); prunes when a signed-rank test says the gap is real.
- **`ThresholdPruner`**, **`PatientPruner`**, **`NopPruner`** — absolute bounds,
  patience for noisy curves, and an A/B control.

!!! warning "Pruning punishes slow starters"
    It is a bandit strategy: a low learning rate that would have won at epoch 200
    gets cut at epoch 20. `n_warmup_steps` is the dial that buys it time.

The `optuna-integration` package ships ready-made callbacks
(`LightGBMPruningCallback`, `XGBoostPruningCallback`,
`PyTorchLightningPruningCallback`) so you don't write the loop.

## Storage and parallelism

Without a storage URL the study dies with the process. With one it is durable,
resumable, and shared:

```python
study = optuna.create_study(
    study_name="gbdt", storage="sqlite:///optuna.db", load_if_exists=True)
```

- `load_if_exists=True` makes the call idempotent — create if new, attach if not.
- Resuming is free: another `study.optimize(objective, n_trials=50)` continues
  with the sampler's model warm.
- **Parallelism is running the same script *N* times** against the same storage.
  No coordinator; each worker reads history, samples, writes back.

```bash
for i in 1 2 3 4; do python tune.py & done
```

SQLite locks under contention — use PostgreSQL for a cluster, or `JournalStorage`
(append-only file) on a shared filesystem. `study.optimize(n_jobs=4)` is
*thread*-based and mostly useless for CPU-bound Python objectives; prefer the
process pattern. See [Concurrency](../python/language/concurrency/README.md).

```python
study.enqueue_trial({"learning_rate": 0.05, "max_depth": 6})   # seed today's prod config
```

## Ask-and-tell

When the evaluation can't be a function Optuna calls — it runs on a cluster, or a
human judges it — invert the control flow:

```python
trial = study.ask()
lr = trial.suggest_float("lr", 1e-4, 1e-1, log=True)
study.tell(trial, run_somewhere_else(lr))
```

## With scikit-learn

Wrap [`cross_val_score`](scikit-learn/cross-validation.md) — the explicit route,
and the one that keeps every leakage rule intact:

```python
def objective(trial):
    pipe = Pipeline([...])       # a Pipeline, never a bare estimator
    return -cross_val_score(pipe, X, y, cv=TimeSeriesSplit(5, gap=10),
                            scoring="neg_mean_absolute_error").mean()
```

Optuna replaces the *search strategy*, not the *validation protocol*: explicit
splitter, `gap` on time series, preprocessing inside the
[Pipeline](scikit-learn/pipelines.md).

`OptunaSearchCV` (from `optuna-integration`) is the drop-in alternative — same
`fit`/`best_params_`/`best_estimator_` surface as `RandomizedSearchCV`, so it
nests for honest scoring — but it takes a static distribution dict, giving up
conditionals and define-by-run.

## Reading the run

```python
study.trials_dataframe()                        # one row per trial
optuna.importance.get_param_importances(study)  # fANOVA, sums to 1
optuna.visualization.plot_optimization_history(study)
optuna.visualization.plot_slice(study)          # value vs each parameter
optuna.visualization.plot_contour(study, params=["lr", "max_depth"])
optuna.visualization.plot_intermediate_values(study)   # curves, pruned included
```

Importance comes from **fANOVA** (functional analysis of variance): fit a random
forest to (parameters → value), then decompose that surrogate's variance across
parameters. It describes *the region you sampled* — a parameter looks
unimportant either because it doesn't matter or because your range was too
narrow. `optuna-dashboard` renders all of this live against a running study.

!!! warning "`best_value` is a maximum over noisy estimates"
    Every objection to `GridSearchCV.best_score_` applies with **more** force,
    because Optuna is better at finding maxima — including the ones that are pure
    fold noise. Report a nested-CV score or a sealed period, never
    `study.best_value`, and record `len(study.trials)`: the count of
    configurations tried deflates everything you report. In finance this is
    [backtest overfitting](concepts/time-series-validation.md).

## When not to reach for it

- **Under ~20 affordable evaluations** — TPE spends its first 10 on random draws
  anyway. Use random search.
- **One or two parameters over a small discrete set** — a grid gives you the full
  surface to plot, which beats a winner.
- **The bottleneck is features, not knobs** — which it usually is. Tuning buys a
  few percent; a better feature or a fixed
  [leak](concepts/data-leakage.md) buys more.

## Related

- [Hyperparameter Search](scikit-learn/hyperparameter-search.md) — grid, random, and halving, and why the exhaustive product doesn't scale
- [Running Cross-Validation](scikit-learn/cross-validation.md) — the loop the objective usually wraps
- [Time-Series Validation](concepts/time-series-validation.md) — the protocol tuning must not break
- [Model Validation](concepts/model-validation.md) — selection bias on the maximum, and nested CV
