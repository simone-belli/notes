# MLflow

An experiment-tracking library: log a run's parameters, metrics, and
artifacts, then query them back later. The payoff is that "how many
configurations have I searched?" or "what params produced this score?" become
queries against a stored record, not something reconstructed from memory or
scrollback — the property [Tuning a Trading Strategy](concepts/strategy-tuning.md)
relies on for logging the trial count `K` before deflating a Sharpe ratio.
MLflow ships three other components (Projects, Models, Model Registry) for
packaging and serving; only **Tracking** is covered here.

```python
import mlflow

with mlflow.start_run():
    mlflow.log_param("learning_rate", 0.01)
    mlflow.log_metric("val_loss", 0.39, step=1)   # step= makes it a series
    mlflow.set_tag("stage", "prototype")
    mlflow.log_artifact("predictions.csv")
```

- `log_param` — inputs, set once per run (config, hyperparameters).
- `log_metric` — outputs, optionally a series over `step` (loss curves).
- `set_tag` — bookkeeping metadata (git SHA, "candidate" vs "prototype"); same
  storage as params, kept separate purely by convention.
- `log_artifact(path)` copies the file's bytes into the run's store — not a
  pointer to wherever it was saved.
- Without an explicit `start_run()`, the first `log_*` call auto-creates one;
  fine for a one-off, but you lose control over naming and nesting.

## Backend store and tracking URI

```python
mlflow.set_tracking_uri("file:./mlruns")          # default — local files
mlflow.set_tracking_uri("sqlite:///mlflow.db")    # queryable, concurrency-safe
mlflow.set_tracking_uri("http://localhost:5000")  # a tracking server
```

With nothing configured, MLflow writes to a local `file:./mlruns` directory —
one subfolder per experiment, one per run, holding plain `params/`, `metrics/`,
`tags/`, `artifacts/` files. It works alone but has no locking, so concurrent
writers race; `sqlite:///` or Postgres/MySQL moves the structured data (params,
metrics, tags) into a real database while artifacts (files) stay wherever
configured separately — the same database/blob-store split
[Optuna](optuna.md#storage-and-parallelism)'s `storage=` uses, for the same
reason.

Runs are scoped to an **experiment**
(`mlflow.set_experiment("name")`, created on first use). `mlflow ui` serves
the table/plot view against whichever store it's pointed at.

## Querying — the actual point

```python
runs = mlflow.search_runs(experiment_names=["strategy-tuning"])
len(runs)   # K — read from the record, not remembered

runs = mlflow.search_runs(
    experiment_names=["strategy-tuning"],
    filter_string="params.max_depth = '6' and metrics.sharpe > 0.5",
)
```

`search_runs` returns a pandas `DataFrame` (`params.*`, `metrics.*`, `tags.*`
columns) — a direct query against the backend store, not a reconstruction.
`MlflowClient` (`from mlflow import MlflowClient`) gives the same access
without the DataFrame wrapper, useful for pulling a single run by ID.

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

!!! note "Optuna has the same shape — MLflow gives you a queryable copy of it"
    `optuna.integration.MLflowCallback` logs each Optuna trial as a nested
    MLflow run automatically. Optuna's `Study`/`Trial` owns the sampling
    decisions; MLflow's parent/child runs own the durable, queryable record —
    both matter at once, but build the loop above by hand first so the
    parent/child mechanics stay visible before adding the callback.

!!! warning "The file store has no locking"
    `file:./mlruns` is fine solo. Parallel writers (multiple trial processes)
    racing on the same run files is the concurrency failure mode a database
    backend (`sqlite:///`, Postgres) exists to remove.

## Related

- [Optuna](optuna.md) — the trial-count deflation warning this note's querying
  section makes concrete; Optuna's own `storage=` solves the same
  durable-record problem, scoped to one study
- [Tuning a Trading Strategy](concepts/strategy-tuning.md) — Rule 3: log `K`
  before the search runs, because deflation can't reconstruct it afterwards
