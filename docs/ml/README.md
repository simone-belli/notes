# Machine Learning

Modelling workflow — the library-agnostic protocol first, then the library.

<div class="grid cards" markdown>

-   :material-folder-outline:{ .lg .middle } __[Concepts](concepts/)__

    ---

    Library-agnostic foundations: what makes a validation score honest, and the leakage that quietly makes it a lie

-   :material-text-box-outline:{ .lg .middle } __[DVC](dvc.md)__

    ---

    Data versioning via Git-like pointer files, remote storage, and reproducible pipeline DAGs

-   :material-text-box-outline:{ .lg .middle } __[MLflow](mlflow.md)__

    ---

    Experiment tracking: the setup workflow, params, metrics, and artifacts as a queryable record, and the web interface over it

-   :material-text-box-outline:{ .lg .middle } __[MLflow — Nested Runs](mlflow-nested-runs.md)__

    ---

    Recording a study of trials as a parent/child run tree, wiring it to an Optuna search, and recovering the trial count

-   :material-text-box-outline:{ .lg .middle } __[Optuna](optuna.md)__

    ---

    Hyperparameter optimisation beyond the grid: define-by-run search spaces, the suggest API, TPE sampling, and pruning

-   :material-text-box-outline:{ .lg .middle } __[Optuna — Studies](optuna-studies.md)__

    ---

    Running a study: durable storage and parallelism, ask-and-tell, the scikit-learn objective, and reading the finished run

-   :material-folder-outline:{ .lg .middle } __[scikit-learn](scikit-learn/)__

    ---

    Classical ML in Python: the estimator API, pipelines, and leakage-safe evaluation

</div>
