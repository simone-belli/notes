# Machine Learning / DVC

Data Version Control — Git-like versioning for files too big for Git, plus a pipeline layer that makes "is this result stale?" a computed answer instead of a remembered one.

:material-text-box-outline: **[Pipelines](pipelines.md){ .lvl-intermediate }**
:   `dvc.yaml` stages as a dependency graph, parameter files and interpolation, `dvc repro`'s hash-based staleness check, `dvc.lock`, and metric diffs

:material-card-bulleted-outline: **[Versioning](versioning.md){ .lvl-intermediate }**
:   Pointer files, the content-addressed cache and its link modes, config layers, and the Git ↔ DVC command mapping

:material-card-bulleted-outline: **[Workflow](workflow.md){ .lvl-basic }**
:   The day-to-day command sequence: setup, the repro/commit/push loop, cloning, moving through history, and `dvc exp`
