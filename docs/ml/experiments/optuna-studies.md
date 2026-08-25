# Optuna — Studies

Beyond defining a search space and letting [Optuna](optuna.md) run it: making a
study durable and resumable, spreading it across workers, wrapping a
scikit-learn objective, recording more than the objective scalar, and reading
the finished run back.

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
process pattern. See [Concurrency](../../python/language/concurrency/README.md).
[MLflow](mlflow.md) solves the same durable-record problem more generally —
this storage is the *operational* record (resumption, worker coordination),
MLflow's is the *reporting* one; see
[MLflow — Nested Runs](mlflow-nested-runs.md) for wiring the two together, and why
process-local MLflow runs don't nest across parallel workers.

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

Wrap [`cross_val_score`](../scikit-learn/cross-validation.md) — the explicit route,
and the one that keeps every leakage rule intact:

```python
def objective(trial):
    pipe = Pipeline([...])       # a Pipeline, never a bare estimator
    return -cross_val_score(pipe, X, y, cv=TimeSeriesSplit(5, gap=10),
                            scoring="neg_mean_absolute_error").mean()
```

Optuna replaces the *search strategy*, not the *validation protocol*: explicit
splitter, `gap` on time series, preprocessing inside the
[Pipeline](../scikit-learn/pipelines.md). For a trading strategy, don't route
through `cross_val_score` at all — pool the out-of-fold predictions and score
once; see [Tuning a Trading Strategy](../concepts/strategy-tuning.md).

`OptunaSearchCV` (from `optuna-integration`) is the drop-in alternative — same
`fit`/`best_params_`/`best_estimator_` surface as `RandomizedSearchCV`, so it
nests for honest scoring — but it takes a static distribution dict, giving up
conditionals and define-by-run.

## Recording more than the objective

The objective returns one float, but that is only what Optuna *optimises* — not
all it stores. Three mechanisms, chosen by the shape of the extra data:

| Extra data | Mechanism |
|---|---|
| A few scalars/strings per trial | `trial.set_user_attr` |
| A series along a step axis | `trial.report(value, step)` |
| Files — predictions, plots, checkpoints | `optuna.artifacts.upload_artifact` |

```python
def objective(trial):
    result = backtest(...)
    trial.set_user_attr("sharpe", float(result.sharpe))
    trial.set_user_attr("turnover", float(result.turnover))
    trial.set_user_attr("fold_scores", [float(s) for s in result.folds])
    return -float(result.sharpe)

study.best_trial.user_attrs["turnover"]
study.trials_dataframe()          # gains user_attrs_sharpe, user_attrs_turnover, ...
```

- Each call writes to storage immediately, so the value survives the process
  **and survives the trial failing** — the natural place to stash a diagnostic
  before an exception propagates. It is a round-trip per call, so keep it out of
  per-epoch loops.
- `study.set_user_attr("commit", sha)` for run-level metadata;
  `study.enqueue_trial(params, user_attrs={...})` to tag a hand-seeded trial.
  `system_attrs` is Optuna's own bookkeeping — don't write to it.
- Set them **inside** the objective. A `callbacks=[...]` function receives a
  read-only `FrozenTrial`; `set_user_attr` there never reaches storage.

!!! warning "In-memory storage doesn't enforce JSON"
    Real backends `json.dumps` attribute values into a text column, so
    `np.float64`, `pd.Timestamp` and estimator objects raise — cast with
    `float()` / `.isoformat()` / `.tolist()`. The default in-memory storage just
    parks the object in a dict, so anything works until the day you add
    `storage="sqlite:///optuna.db"`. Assume the JSON rule from the start, and
    store *paths* rather than large arrays.

Curves belong in `trial.report`, not a user attribute — it has its own storage
table, feeds the pruners, and plots via `plot_intermediate_values`. Files belong
in an artifact store (Optuna ≥ 3.3), which `optuna-dashboard` renders inline:

```python
from optuna.artifacts import FileSystemArtifactStore, upload_artifact

store = FileSystemArtifactStore(base_path="./artifacts")
upload_artifact(artifact_store=store, file_path=path, study_or_trial=trial)
```

The payoff is **post-hoc selection**: with turnover, trade count and drawdown as
columns, `trials_dataframe()` is a table you filter *after* the search — pick the
best trial among those meeting your constraints, instead of encoding every
constraint into the objective scalar up front. For constraints that are genuinely
hard, `TPESampler(constraints_func=...)` reads the same `trial.user_attrs`.

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
    backtest overfitting — see
    [Tuning a Trading Strategy](../concepts/strategy-tuning.md) for how much Sharpe
    a zero-skill model buys from 20 trials.


## Related

- [Optuna](optuna.md) — define-by-run search spaces, the suggest API, samplers, and pruning
- [MLflow — Nested Runs](mlflow-nested-runs.md) — mapping study/trial onto parent/child runs
- [Running Cross-Validation](../scikit-learn/cross-validation.md) — the loop the objective usually wraps
- [Tuning a Trading Strategy](../concepts/strategy-tuning.md) — what the objective should return, and what to report instead of `best_value`
