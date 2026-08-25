# DVC — Pipelines

`dvc.yaml` describes a directed acyclic graph (DAG) of reproducible stages —
the part of DVC (Data Version Control) that has no Git equivalent. Each stage
declares its dependencies explicitly, so staleness becomes something DVC
*computes* by comparing hashes rather than something a person has to
*remember* ("did I retrain after changing the params?").

!!! note "Computed, not remembered"
    It's the same move as a `Makefile` target listing its prerequisites so
    `make` computes rebuild-or-skip instead of a person tracking it by hand —
    and the same move as a leakage boundary (see
    [Data Leakage](../concepts/data-leakage.md)'s "structure beats vigilance"
    tip): both replace a fact a human must remember with a fact a tool
    enforces or computes, just applied to files instead of cross-validation
    folds.

## Anatomy of a stage

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

## Where parameters go

`params.yaml`, beside the `dvc.yaml` that references it — the default file DVC
reads whenever a stage names a bare key. It is Git-tracked like source, not a
DVC output: small, human-diffable, and the file `dvc params diff` reads across
revisions.

```yaml
# params.yaml
prepare:
  test_size: 0.2
train:
  n_estimators: 300
  learning_rate: 0.05
```

- Stages reference **keys**, never the file: `params: [train.n_estimators]`.
  Naming a group (`params: [train]`) tracks every key under it.
- Nesting is arbitrary — a dotted path addresses any depth
  (`train.optimizer.lr`).
- DVC only *hashes* the values; it injects nothing into the process. The
  script loads the file itself (`yaml.safe_load`, or `dvc.api.params_show()`).
- `dvc stage add -p train.n_estimators ...` adds the entry from the CLI.

!!! warning "A hard-coded constant is invisible to invalidation"
    Anything the script reads but the stage doesn't declare under `params` is
    outside the hash, so editing it leaves `dvc repro` convinced the stage is
    up to date. That is the same failure the DAG exists to remove, so a
    tunable belongs in `params.yaml` rather than at the top of `train.py`.

### Reading from a file other than `params.yaml`

There is no repo-wide setting that renames the default — an alternative file
is named at the point of use instead. In `params:`, a bare string means
`params.yaml`; a `file:` mapping means that file:

```yaml
    params:
      - train.n_estimators          # implicit: params.yaml
      - configs/model.yaml:         # explicit file, selected keys
          - lr
          - epochs
      - configs/sweep.toml:         # no keys listed → every key in the file
```

- YAML, JSON, TOML, and Python modules all work; the extension picks the
  parser, so an alternative file needn't be YAML at all.
- Paths resolve relative to the `dvc.yaml`, like `deps` and `outs`.
- The CLI form colon-separates and comma-joins:
  `dvc stage add -p configs/model.yaml:lr,epochs ...`.
- `params.yaml` is not implied once a custom file is listed — a stage can read
  only `configs/model.yaml` and never touch the default.
- Commands take the path too: `dvc params diff configs/model.yaml`,
  `dvc exp run -S 'configs/model.yaml:lr=0.1'`.

Splitting per-stage files keeps invalidation tight, but one `params.yaml` is
usually enough: key-level tracking already means an unrelated edit in the same
file won't touch a stage that never reads that key. The real reasons to
split are a config a non-DVC tool also consumes, or one file per pipeline in a
multi-`dvc.yaml` repo.

### Interpolating them into `cmd`

```yaml
vars:
  - configs/model.yaml           # adds its keys to the substitution scope
  - configs/model.yaml:train     # or import just one section
  - seed: 42                     # inline literal, no file

stages:
  train:
    cmd: python train.py --lr ${lr} --seed ${seed}
```

- `${...}` resolves against `params.yaml` implicitly; `vars:` is what brings
  an alternative file into scope, and accepts a per-stage form as well.
- Keys land **flat** — a file listed in `vars:` is not namespaced by its path,
  so `${lr}`, not `${configs/model.yaml:lr}`. Two files defining the same
  top-level key is an error, not a silent last-one-wins.
- Interpolated params are tracked automatically — they land in `dvc.lock`
  without appearing under `params`.
- Inline `vars:` values aren't params, but they change the *resolved* `cmd`,
  which invalidates the stage anyway.

### Reading them back in Python

`dvc.api.params_show()` returns every tracked param as a dict, resolved from
whichever files the stages declare — the alternative to hard-coding a second
`open()` in the script.

```python
from dvc.api import params_show

params_show()                            # all tracked params, merged
params_show("configs/model.yaml")        # one file
params_show(stages="train")              # only what `train` declares
```

### Changing a value for one run

`dvc exp run -S train.learning_rate=0.1` writes the override into
`params.yaml`, then runs — so the experiment is recorded against a real param
value rather than an untracked flag. See [Workflow](workflow.md) for where
`dvc exp` fits.

## Running the pipeline

### `dvc repro`

Walks the DAG and skips any stage whose `deps`/`params` hashes still match the
last recorded run, re-running only what actually changed — robust to a
`touch`ed-but-unmodified file the way timestamp-based `make` isn't, since it
hashes content rather than checking mtimes.

### `dvc.lock`

The machine-written, pinned record `dvc repro` compares against: `dvc.yaml` is
the declared intent, `dvc.lock` is the exact hashes that produced the current
outputs — the same relationship a manifest (`pyproject.toml`) has to its lock
file (`poetry.lock`).

- Commit it, the same way you'd commit
  [`poetry.lock`](../../python/tooling/poetry.md).
- `git checkout` of an old commit plus `dvc checkout` then restores not just
  old code but the exact data/param hashes that made that run reproducible.

## Where the file goes

At the **repo root**, beside `.git/` and `.dvc/` — the default, and the right
answer for a project with one pipeline. Write it by hand, or let DVC append a
stage to the `dvc.yaml` in the current directory:

```bash
dvc stage add -n prepare \
  -d prepare.py -d data/raw.csv \
  -o data/clean.csv \
  python prepare.py data/raw.csv data/clean.csv
```

### Paths resolve relative to the file

Every path in it — `deps`, `outs`, `cmd`'s working directory, and the default
`params.yaml` — resolves relative to **the `dvc.yaml`'s own directory**, not
the repo root (the same rule `.dvc` pointer files follow). Moving the file
into a subdirectory moves the whole coordinate system with it. A stage can
override just its command's working directory with `wdir:`, usually the better
answer than splitting the file when one script insists on being run from
elsewhere.

### More than one pipeline

Multiple `dvc.yaml` files are allowed, one per subdirectory — for a monorepo
holding genuinely separate pipelines. Each gets its own `dvc.lock` beside it.

- `dvc repro` acts on the `dvc.yaml` in the current directory.
- `dvc repro -P` (`--all-pipelines`) runs every pipeline in the repo.
- `dvc repro path/to/dvc.yaml:train` targets one stage.

!!! warning "One file until the pipelines are genuinely independent"
    Splitting early costs the thing that makes `dvc repro` worth using: a
    single DAG that propagates invalidation end to end. Two files mean two
    lock files, and a plain `dvc repro` in one directory silently leaves the
    other pipeline stale — reintroducing the "did I remember to re-run it?"
    question the DAG exists to answer. Add subdirectories only when no output
    of one pipeline is an input to the other.

## Inspecting and comparing

### `dvc dag`

Renders the stage graph read-only from `dvc.yaml`'s declared deps/outs (add
`--mermaid` for [flowchart syntax](../../tools/mermaid.md)) — the pipeline
equivalent of `git log --graph`, useful for spotting a typo'd path that
silently leaves a stage disconnected from the graph instead of erroring.

### `dvc metrics diff` / `dvc params diff`

Compare metrics and hyperparameters across Git revisions. This overlaps with
what an experiment tracker like [MLflow](../experiments/mlflow.md) does, but
DVC's comparisons are anchored to Git commits rather than an independent run
database.

## Related

- [Versioning](versioning.md) — the pointer files and cache stages are built on
- [Workflow](workflow.md) — where `dvc repro` sits in the daily loop
