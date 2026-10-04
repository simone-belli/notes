# Machine Learning / Experiments

Running hyperparameter searches and keeping a durable record of what was tried — Optuna proposes the configurations, MLflow remembers them.

:material-text-box-outline: **[MLflow](mlflow.md){ .lvl-basic }**
:   Experiment tracking: the setup workflow, params, metrics, and artifacts as a queryable record, and the web interface over it

:material-text-box-outline: **[MLflow — Nested Runs](mlflow-nested-runs.md){ .lvl-advanced }**
:   Recording a study as a parent/child run tree, wiring it to an Optuna search, and recovering the trial count

:material-text-box-outline: **[Optuna](optuna.md){ .lvl-intermediate }**
:   Hyperparameter optimisation beyond the grid: define-by-run search spaces, the suggest API, TPE and grid sampling, and pruning

:material-text-box-outline: **[Optuna — Distributions](optuna-distributions.md){ .lvl-advanced }**
:   The objects behind `suggest_*`: the three distribution classes, the JSON round-trip, compatibility checks, and injecting trials you already know

:material-text-box-outline: **[Optuna — Pruning](optuna-pruning.md){ .lvl-advanced }**
:   Stopping a trial early and scoring one that blew up — the pruners, what `PRUNED` costs the sampler, capping at the constant-predictor loss, and the divergence detectors

:material-text-box-outline: **[Optuna — Studies](optuna-studies.md){ .lvl-advanced }**
:   Running a study: durable storage and parallelism, ask-and-tell, the scikit-learn objective, and reading the finished run
