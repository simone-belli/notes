# Machine Learning / Experiments

Running hyperparameter searches and keeping a durable record of what was tried — Optuna proposes the configurations, MLflow remembers them.

:material-text-box-outline: **[MLflow](mlflow.md){ .lvl-basic }**
:   Experiment tracking: the setup workflow, params, metrics, and artifacts as a queryable record, and the web interface over it

:material-text-box-outline: **[MLflow — Nested Runs](mlflow-nested-runs.md){ .lvl-advanced }**
:   Recording a study of trials as a parent/child run tree, wiring it to an Optuna search, and recovering the trial count

:material-text-box-outline: **[Optuna](optuna.md){ .lvl-intermediate }**
:   Hyperparameter optimisation beyond the grid: define-by-run search spaces, the suggest API, TPE sampling, and pruning

:material-text-box-outline: **[Optuna — Studies](optuna-studies.md){ .lvl-advanced }**
:   Running a study: durable storage and parallelism, ask-and-tell, the scikit-learn objective, and reading the finished run
