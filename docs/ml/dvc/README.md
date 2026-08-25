# Machine Learning / DVC

Data Version Control — Git-like versioning for files too big for Git, plus a pipeline layer that makes "is this result stale?" a computed answer instead of a remembered one.

:material-text-box-outline: **[Pipelines](pipelines.md)**
:   `dvc.yaml` stages as a dependency graph, where the file goes, where parameters are defined (`params.yaml` or an alternative file) and interpolated, `dvc repro`'s hash-based staleness check, `dvc.lock`, and metric/param diffs

:material-card-bulleted-outline: **[Versioning](versioning.md)**
:   Where `dvc init` goes, pointer files, the content-addressed cache and its link modes, auto-managed `.gitignore`, the committed vs. local config layers, and the Git ↔ DVC command mapping

:material-card-bulleted-outline: **[Workflow](workflow.md)**
:   The day-to-day command sequence: setup, the repro/commit/push loop, cloning, moving through history, and `dvc exp`
