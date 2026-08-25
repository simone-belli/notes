# MLflow — Nested Runs

A hyperparameter study is two levels — one search, many trials — and
[MLflow](mlflow.md) records that shape with **nested runs**: a parent run for
the study, one child run per trial. This is also what makes an
[Optuna](optuna.md) search legible after the fact, and what makes the trial
count `K` recoverable for deflating a reported metric.

## Nested runs — study and trial

```python
with mlflow.start_run(run_name="study") as parent:
    mlflow.log_param("search_space", "lr:[1e-4,1e-1], depth:[2,12]")

    for cfg in configs:
        with mlflow.start_run(run_name=f"trial-{cfg['id']}", nested=True):
            mlflow.log_params(cfg)
            mlflow.log_metric("score", evaluate(cfg))
```

- `nested=True` is required on the child — without it MLflow assumes you meant
  to end the parent and start a sibling, and raises.
- Each child gets a `mlflow.parentRunId` tag, which the UI uses to draw the
  tree and `filter_string="tags.mlflow.parentRunId = '<id>'"` uses to pull one
  study's trials — so `len(...)` scoped to one parent is `K` for *that* study,
  the granularity a deflation calculation wants.
- Search-space-level metadata (constant across trials) belongs on the parent;
  per-trial params/metrics on the children.

!!! warning "The file store has no locking"
    `file:./mlruns` is fine solo. Parallel writers (multiple trial processes)
    racing on the same run files is the concurrency failure mode a database
    backend (`sqlite:///`, Postgres) exists to remove.

## With Optuna

[Optuna](optuna.md) and MLflow both have a two-level study/trial hierarchy,
which is why they compose without forcing. The division of labour:

- **Optuna's `storage=`** is the *operational* record — resuming with the
  sampler's model warm, coordinating parallel workers, holding the pruners'
  intermediate values. Scoped to one study.
- **MLflow** is the *reporting* record — every run of every kind (trials,
  one-off fits, backtests) in one place, with artifacts, comparable across
  studies and across time.

If the work is only ever hyperparameter optimisation and only ever local,
Optuna storage plus `optuna-dashboard` is enough — don't add MLflow for its
own sake.

| Optuna | MLflow |
|---|---|
| `Study` | parent run |
| `Trial` | child run (`nested=True`) |
| `trial.params` | `log_params` on the child |
| objective return value | `log_metric` on the child |
| `trial.user_attrs` | tags on the child |
| `trial.report(v, step)` | `log_metric(..., step=step)` on the child |

### `MLflowCallback`

```bash
pip install optuna-integration[mlflow]
```

```python
from optuna.integration.mlflow import MLflowCallback

mlflc = MLflowCallback(tracking_uri="sqlite:///mlflow.db", metric_name="rmse")
study = optuna.create_study(study_name="gbdt-tuning", direction="minimize")
study.optimize(objective, n_trials=100, callbacks=[mlflc])
```

- One MLflow run per trial; `trial.params` → params, return value → a metric
  named `metric_name`; trial number, state, and timings → tags.
- The **study name becomes the experiment name** — pass an explicit
  `study_name` to `create_study` or you get `no-name-a1b2c3d4`.
- `tag_trial_user_attrs=True` (default) carries `set_user_attr` values across
  as tags, so post-hoc selection columns come over for free.
- Runs are **flat** by default. For the parent/child tree, wrap the optimise
  call and forward `nested=True` through `mlflow_kwargs`:

```python
mlflc = MLflowCallback(
    tracking_uri="sqlite:///mlflow.db",
    metric_name="rmse",
    create_experiment=False,           # stop it re-pointing the experiment
    mlflow_kwargs={"nested": True},    # passthrough to start_run
)

mlflow.set_experiment("strategy-tuning")
with mlflow.start_run(run_name="study-2024-06"):
    mlflow.log_params({"sampler": "TPE", "seed": 42, "n_trials": 100})
    study.optimize(objective, n_trials=100, callbacks=[mlflc])
    mlflow.log_metric("best_value", study.best_value)
```

A callback receives a read-only `FrozenTrial` *after* the trial ends, so it
cannot log curves, plots, or model files. `track_in_mlflow()` makes the
trial's run active during the objective body, which fixes that:

```python
@mlflc.track_in_mlflow()
def objective(trial):
    ...
    mlflow.log_metric("val_score", score, step=epoch)   # lands in this trial's run
    mlflow.log_artifact("curve.png")
```

### Logging manually

More code, total control — and the better path to build the reflex first,
since the callback hides exactly the mechanics worth internalising:

```python
def objective(trial):
    with mlflow.start_run(nested=True, run_name=f"trial-{trial.number}"):
        params = {"lr": trial.suggest_float("lr", 1e-4, 1e-1, log=True)}
        mlflow.log_params(params)

        for step, score in enumerate(train_iter(**params)):
            trial.report(score, step)                         # what the pruner reads
            mlflow.log_metric("val_score", score, step=step)  # what the UI draws
            if trial.should_prune():
                mlflow.set_tag("trial_state", "PRUNED")
                raise optuna.TrialPruned()

        mlflow.log_artifact("predictions.csv")
        return score
```

The duplicated value on those two lines is intentional — neither call
substitutes for the other.

!!! warning "A pruned trial ends its MLflow run as FAILED"
    `TrialPruned` propagates out of the `with` block and the context manager
    treats any exception as failure, so a healthy pruned trial records as
    `FAILED`. Tag it before raising to keep it distinguishable from a real
    crash; to fix the status itself, manage the run manually
    (`mlflow.start_run(...)` / `mlflow.end_run(status="FINISHED")`).

!!! warning "Parallelism breaks the nesting"
    MLflow's active run is **process-local**, but Optuna parallelism is N
    processes against one storage — so a parent opened in one process is
    invisible to the others and `nested=True` has nothing to attach to.
    Group flat runs with an explicit tag instead
    (`mlflow.set_tag("study_name", study.study_name)`, then filter on it);
    MLflow's own nesting is itself just a `mlflow.parentRunId` tag, so this
    is the same mechanism at a level you control.

### Recovering K

```python
trials = mlflow.search_runs(
    experiment_names=["strategy-tuning"],
    filter_string=f"tags.mlflow.parentRunId = '{parent_run_id}'",
)
K = len(trials)
```

Better than `len(study.trials)` on two counts: it survives the study object,
and it spans restarts. `load_if_exists=True` with three rounds of
`optimize(n_trials=50)` is a K of 150 — and abandoning one study to start
another doesn't reset the count for deflating whatever you eventually report.
A record spanning studies is what makes the honest number recoverable at all.
Log the sampler seed on the parent while you're there; reproducing a study
needs the seed and the count together
([Reproducibility and Seeding](concepts/reproducibility.md)).

## Related

- [MLflow](mlflow.md) — the tracking API, the workflow, backend stores, and
  querying that this note builds on
- [Optuna](optuna.md) — the search this note wires MLflow to
- [Tuning a Trading Strategy](concepts/strategy-tuning.md) — Rule 3: log `K`
  before the search runs, because deflation can't reconstruct it afterwards
- [Reproducibility and Seeding](concepts/reproducibility.md) — the sampler
  seed worth logging alongside the trial count
