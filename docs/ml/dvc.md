# DVC

DVC (Data Version Control) is a CLI tool that gives large files (datasets,
model weights) Git-like version control without putting their bytes into
Git. Git diffs and stores text efficiently but duplicates a large binary on
every commit that touches it; DVC keeps the bytes out of `.git/` while still
tying their identity to Git history. It layers on top of an existing Git
repo — it doesn't replace it.

```bash
git init
dvc init                 # like `git init`, but creates .dvc/
```

## Pointer files: the core trick

`dvc add` moves a file into a hash-addressed cache and replaces it with a
small pointer file that Git tracks instead:

```bash
dvc add data/raw.csv     # -> data/raw.csv.dvc + .gitignore entry
git add data/raw.csv.dvc data/.gitignore
git commit -m "add raw dataset v1"
```

`data/raw.csv.dvc` is YAML holding the file's hash and size. Git only ever
sees this tiny pointer — never the dataset itself — so the dataset's
*identity* is versioned in Git history even though its bytes live elsewhere.
This mirrors how Git itself stores blobs by content hash (see
[Git Internals: The Object Model](../git/internals.md)), just with one more
layer of indirection to keep the big bytes out of `.git/objects`.

## Git ↔ DVC command mapping

| Git | DVC | Effect |
|---|---|---|
| `git remote` | `dvc remote` | points at bulk storage: S3, GCS, Azure, SSH, network folder |
| `git push` | `dvc push` | uploads cached files to remote storage |
| `git pull` | `dvc pull` | downloads cache files matching the checked-out pointers |
| `git checkout <rev>` | `dvc checkout` | swaps large files to match the currently checked-out `.dvc` pointers |
| `git status` | `dvc status` | reports which tracked files/pipeline outputs are out of sync |
| `git diff` | `dvc diff` | compares hash/size between revisions (not line content) |

!!! note "Every Git operation still works"
    Because the pointer file is the only thing Git tracks, branches, tags,
    `git log -- data/raw.csv.dvc`, pull requests, and merge conflicts on the
    pointer file all behave exactly like they would for any other text file.

```bash
dvc remote add -d storage s3://my-bucket/dvc-store
git add .dvc/config
git commit -m "configure dvc remote"
dvc push
```

The remote is not Git-aware — it's a flat, hash-keyed blob store DVC talks to
directly over S3/GCS/SSH, parallel to how a Git remote stores hash-named
commit objects but reached over the Git smart-protocol instead.

## Pipelines (no Git equivalent)

`dvc.yaml` describes a DAG of reproducible stages; `dvc repro` re-runs only
the stages whose dependencies (code or data, by hash) changed — a Makefile
with hash-based rather than timestamp-based invalidation:

```yaml
stages:
  train:
    cmd: python train.py data/clean.csv
    deps: [train.py, data/clean.csv]
    outs: [model.pkl]
    metrics: [metrics.json]
```

`dvc.lock` records the exact hashes that produced current outputs — commit
it, the same way you'd commit `poetry.lock`. `dvc metrics diff` / `dvc params
diff` compare metrics and hyperparameters across Git revisions; this overlaps
with what an experiment tracker like [MLflow](mlflow.md) does, but DVC's
comparisons are anchored to Git commits rather than an independent run
database.

!!! tip "DVC vs. Git LFS"
    Git Large File Storage (Git LFS) solves the same problem with a similar
    pointer-file trick, but is tied to a specific Git host's LFS server and
    has no pipeline concept. DVC remotes are storage you already have
    (S3, GCS, SSH, …), and `dvc.yaml` pipelines add reproducibility on top of
    plain file versioning.
