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

## The workflow

Four steps, and the order is load-bearing — each of the first three sets
process-global state the next one reads:

```python
import mlflow

mlflow.set_tracking_uri("sqlite:///mlflow.db")   # 1. where the record lives
mlflow.set_experiment("strategy-tuning")         # 2. which namespace runs join
with mlflow.start_run(run_name="baseline"):      # 3. one execution
    mlflow.log_params({"learning_rate": 0.01, "max_depth": 6})
    mlflow.log_metric("sharpe", 0.72)
    mlflow.log_artifact("equity_curve.png")

mlflow.search_runs(experiment_names=["strategy-tuning"])   # 4. read it back
```

- Steps 1–2 run once per script; step 3 repeats per run. `set_experiment`
  before `set_tracking_uri` resolves the experiment against the *previous*
  store — the usual cause of runs appearing in a `./mlruns` nobody meant to
  create.
- Skipping step 2 puts everything in the `Default` experiment (ID `0`).
- Both are settable from the environment instead, keeping the store out of the
  code: `MLFLOW_TRACKING_URI`, `MLFLOW_EXPERIMENT_NAME`.
- `mlflow.autolog()` (or the flavour-specific `mlflow.sklearn.autolog()`)
  before a `fit` call logs that library's params, metrics, and model without
  explicit `log_*` calls. A fast start; it logs what the integration chose,
  not what you chose.

### Creating an experiment

`set_experiment` creates on first use with defaults. `create_experiment` is
the explicit form, and the only way to control the artifact location:

```python
mlflow.create_experiment(
    "strategy-tuning",
    artifact_location="file:///path/to/artifacts",   # or s3://bucket/prefix
    tags={"project": "momentum"},
)
mlflow.set_experiment("strategy-tuning")             # still needed to select it
```

- It returns an experiment ID and **raises if the name exists** — it is not
  idempotent, so guard it:

```python
from mlflow import MlflowClient

exp = MlflowClient().get_experiment_by_name("strategy-tuning")
exp_id = exp.experiment_id if exp else mlflow.create_experiment("strategy-tuning")
```

- `artifact_location` is fixed at creation; no API changes it afterwards.
  Left unset, artifacts default to the tracking store's root — for
  `sqlite:///`, that means metadata in the database but artifacts still under
  `./mlruns`.
- `mlflow.set_experiment(experiment_id=...)` selects by ID instead of name,
  useful once the ID is captured.

!!! warning "Deleting an experiment only hides it"
    Deletion sets `lifecycle_stage` to `deleted` and **keeps the name
    reserved**, so re-creating with the same name still raises — the confusing
    case where a name is both "gone" and taken. `client.restore_experiment(id)`
    undoes it; `mlflow gc` is what actually frees the name.

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

Whichever store you configure here is the one the
[web interface](#the-web-interface) has to be pointed at, and the one
[experiments](#creating-an-experiment) resolve against.

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

## The web interface

`mlflow ui` starts a local web user interface (UI) over a tracking store and
serves it on `localhost:5000`:

```bash
mlflow ui                                          # reads ./mlruns, relative to CWD
mlflow ui --port 5001
mlflow ui --backend-store-uri sqlite:///mlflow.db  # match whatever the script logged to
mlflow server --host 0.0.0.0 --port 5000           # the long-running variant
```

- `mlflow ui` resolves `./mlruns` **relative to the working directory it is
  launched from** — an empty run table almost always means the wrong
  directory, not lost data. Pass `--backend-store-uri` explicitly to be sure.
- `mlflow server` is the same app configured for a shared, long-running
  deployment (worker processes, a separate `--artifacts-destination`);
  `mlflow ui` is the local single-user shorthand. Point clients at either
  with `mlflow.set_tracking_uri("http://localhost:5000")`.

What it gives you beyond `search_runs`:

- **Runs table** — one row per run, sortable, with a column picker for
  `params.*` / `metrics.*` / `tags.*`. Nested runs collapse under their parent
  with an expand arrow, so a study reads as one row until opened.
- **The search box takes the same `filter_string` syntax** as `search_runs` —
  prototype a filter interactively, then paste it into code unchanged.
- **Run comparison** — select several runs → *Compare* for parallel
  coordinates, scatter, and contour plots across params against metrics. The
  visual counterpart to reading a `trials_dataframe`.
- **Metric curves** — anything logged with `step=` renders as a line chart on
  the run's page rather than a single number.
- **Artifacts tab** — previews images, text, and CSV inline per run, so
  plots logged with `log_artifact` are viewable without downloading them.

!!! tip "The UI is a read-only view, not a second source of truth"
    Everything it shows comes from the same backend store `search_runs`
    queries. Use it to explore and to eyeball curves; use the query API for
    anything that has to end up in a calculation — such as the trial count
    `K` — so the number is reproducible rather than transcribed by hand.

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

- [Optuna](optuna.md) — the trial-count deflation warning this note's querying
  section makes concrete; Optuna's own `storage=` solves the same
  durable-record problem, scoped to one study
- [Tuning a Trading Strategy](concepts/strategy-tuning.md) — Rule 3: log `K`
  before the search runs, because deflation can't reconstruct it afterwards
- [Reproducibility and Seeding](concepts/reproducibility.md) — the sampler
  seed worth logging alongside the trial count
