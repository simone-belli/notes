---
tags:
  - performance
---

# Optuna

A framework-agnostic library for hyperparameter optimisation (HPO). Where
[`RandomizedSearchCV`](../scikit-learn/hyperparameter-search.md) is *memoryless* —
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

A sampler is a standalone object — construct it, then hand it to
`create_study` via `sampler=`. Nothing about a sampler is study-specific
until that call:

```python
sampler = optuna.samplers.TPESampler(
    seed=42,               # reproducibility needs this, not a global seed
    n_startup_trials=10,   # random draws before the model engages
    multivariate=True,     # joint density — models interactions
    constant_liar=True,    # distributed runs: stops workers proposing the same point
)
study = optuna.create_study(sampler=sampler, direction="minimize")
study.optimize(objective, n_trials=100)
```

- `sampler=` defaults to `TPESampler()` (unseeded) if omitted — passing your
  own instance is the only way to set `seed=` or any other sampler option.
- The sampler is attached to `study`, not to `optimize`: calling
  `study.optimize(...)` again later (resuming, or another batch of trials)
  reuses the same sampler instance and its accumulated state — you don't
  reconstruct or re-pass it per call.
- Swapping samplers means constructing a different object and passing it the
  same way — `optuna.create_study(sampler=optuna.samplers.CmaEsSampler(seed=42))`
  — `create_study` doesn't know or care which sampler class it receives.

The default TPE is **univariate**: one independent density per parameter, so it
cannot represent "high learning rate works, but only with shallow trees".
`multivariate=True` is worth switching on for gradient-boosting spaces.

`seed=` above reproduces only the sampler's proposals — the objective's own
randomness (a train/test split, a model's `random_state`) is a separate seed
you own; see [Reproducibility and Seeding](../concepts/reproducibility.md).

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

## Running and reading a study

Persisting a study so it survives the process, parallelising it, wiring it to
scikit-learn, and reading the result back — see
[Optuna — Studies](optuna-studies.md).

## When not to reach for it

- **Under ~20 affordable evaluations** — TPE spends its first 10 on random draws
  anyway. Use random search.
- **One or two parameters over a small discrete set** — a grid gives you the full
  surface to plot, which beats a winner.
- **The bottleneck is features, not knobs** — which it usually is. Tuning buys a
  few percent; a better feature or a fixed
  [leak](../concepts/data-leakage.md) buys more.


## Related

- [Optuna — Studies](optuna-studies.md) — storage, parallelism, ask-and-tell,
  the scikit-learn objective, and reading the run
- [MLflow](mlflow.md) — the general-purpose durable-record library; see
  [MLflow — Nested Runs](mlflow-nested-runs.md) for mapping study/trial onto parent/child runs
- [Reproducibility and Seeding](../concepts/reproducibility.md) — the sampler's `seed` vs the objective's own
- [Hyperparameter Search](../scikit-learn/hyperparameter-search.md) — grid, random, and halving, and why the exhaustive product doesn't scale
- [Time-Series Validation](../concepts/time-series-validation.md) — the protocol tuning must not break
- [Tuning a Trading Strategy](../concepts/strategy-tuning.md) — what the objective should return, and what to report instead of `best_value`
- [Model Validation](../concepts/model-validation.md) — selection bias on the maximum, and nested CV
