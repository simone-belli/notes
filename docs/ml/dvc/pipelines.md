# DVC — Pipelines

`dvc.yaml` describes a directed acyclic graph (DAG) of reproducible stages —
the part of DVC (Data Version Control) that has no Git equivalent. Each stage
declares its dependencies explicitly, which is the idea worth internalising:
staleness becomes something DVC *computes* by comparing hashes, not something
a person has to *remember* ("did I retrain after changing the params?"). It's
the same move as a `Makefile` target listing its prerequisites so `make`
computes rebuild-or-skip instead of a person tracking it by hand — and the
same move as a leakage boundary (see
[Data Leakage](../concepts/data-leakage.md)'s "structure beats vigilance" tip):
both replace a fact a human must remember with a fact a tool enforces or
computes, just applied to files instead of cross-validation folds.

```yaml
stages:
  prepare:
    cmd: python prepare.py data/raw.csv data/clean.csv
    deps: [prepare.py, data/raw.csv]
    outs: [data/clean.csv]

  train:
    cmd: python train.py
    deps: [train.py, data/clean.csv]      # data/clean.csv chains to `prepare`'s outs
    params: [train.n_estimators]           # a key inside params.yaml, not a file
    outs: [model.pkl]
    metrics: [metrics.json: {cache: false}]
```

- **`deps`/`outs`** chain stages into a DAG — one stage's `outs` is the next
  stage's `deps`, so changing `data/raw.csv` invalidates `prepare`, which
  invalidates `train` in turn, propagating downstream automatically.
- **`params`** invalidates on specific *keys* inside `params.yaml`, not on
  the whole file's hash — so unrelated settings sharing that file don't
  spuriously invalidate a stage that never reads them.
- **`metrics`/`plots`** are `outs` marked for comparison (`dvc metrics diff`,
  `dvc plots show`) rather than caching; `cache: false` skips the DVC cache
  entirely and lets Git track the file directly — sensible for a small,
  human-diffable JSON.

`dvc repro` walks the DAG and skips any stage whose `deps`/`params` hashes
still match the last recorded run, re-running only what actually changed —
robust to a `touch`ed-but-unmodified file the way timestamp-based `make`
isn't, since it hashes content rather than checking mtimes.

`dvc.lock` is the machine-written, pinned record `dvc repro` compares
against: `dvc.yaml` is the declared intent, `dvc.lock` is the exact hashes
that produced the current outputs — the same relationship a manifest
(`pyproject.toml`) has to its lock file (`poetry.lock`). Commit it, the same
way you'd commit [`poetry.lock`](../../python/tooling/poetry.md);
`git checkout` an old commit plus `dvc checkout` restores not just old code
but the exact data/param hashes that made that run reproducible.

`dvc dag` (add `--mermaid` for [flowchart syntax](../../tools/mermaid.md))
renders the stage graph read-only from `dvc.yaml`'s declared deps/outs — the
pipeline equivalent of `git log --graph`, useful for spotting a typo'd path
that silently leaves a stage disconnected from the graph instead of erroring.

`dvc metrics diff` / `dvc params diff` compare metrics and hyperparameters
across Git revisions; this overlaps with what an experiment tracker like
[MLflow](../experiments/mlflow.md) does, but DVC's comparisons are anchored to
Git commits rather than an independent run database.

## Related

- [Versioning](versioning.md) — the pointer files and cache stages are built on
- [Workflow](workflow.md) — where `dvc repro` sits in the daily loop
