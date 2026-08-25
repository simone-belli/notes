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

## Where `dvc init` goes

At the **repo root, beside `.git/`** — one DVC repo per Git repo, always.

- `dvc init` refuses to run outside a Git working tree unless given
  `--no-scm`, which throws away the entire point.
- A DVC repo in a separate directory or repo would let the data version and
  the code version move independently — back to *remembering* which data
  produced a result, the failure the pointer-file design exists to remove.
- Co-located, one commit answers both questions at once: which code produced
  a number, and which bytes it read.

Four different things share the word "where", and only the first is what
`dvc init` decides:

| Thing | Where it lives | In Git? |
|---|---|---|
| `.dvc/` — config and repo metadata | repo root, beside `.git/` | `.dvc/config` yes, `.dvc/cache` no |
| The cache (`.dvc/cache`) | inside `.dvc/` by default; relocatable via `cache.dir` | no — gitignored |
| Tracked data + its `.dvc` pointer | wherever it naturally sits in the tree | pointer yes, bytes no |
| The remote (object store) | outside the repo, necessarily | no — only its URL, in `.dvc/config` |

## Pointer files: the core trick

`dvc add` moves a file into a hash-addressed cache and replaces it with a
small pointer file that Git tracks instead:

```bash
dvc add data/raw.csv     # -> data/raw.csv.dvc + .gitignore entry
git add data/raw.csv.dvc data/.gitignore
git commit -m "add raw dataset v1"
```

`data/raw.csv.dvc` is YAML holding the file's hash and size:

```yaml
outs:
- md5: a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4
  size: 5368709120
  hash: md5
  path: raw.csv
```

`path` is relative to the `.dvc` file's own directory (not the repo root),
so the pointer stays valid if the tracked directory is moved as a whole. Git
only ever sees this tiny pointer — never the dataset itself — so the
dataset's *identity* is versioned in Git history even though its bytes live
elsewhere. This mirrors how Git itself stores blobs by content hash (see
[Git Internals: The Object Model](../git/internals.md)), just with one more
layer of indirection to keep the big bytes out of `.git/objects`. Tracking a
directory instead of a file works the same way, but the `.dvc` file's hash
is of a **directory manifest** (a JSON listing of every contained file's
hash, itself stored in the cache) rather than of any single file's bytes —
marked with a `.dir` suffix so directory hashes and file hashes never
collide in the same hash space.

### The cache: content-addressed, and linked rather than copied

`.dvc/cache` stores objects under a two-character-prefix directory (the same
trick `.git/objects/ab/cdef…` uses to avoid one huge flat directory),
keyed by hash — identical bytes anywhere in the project dedupe to one cache
entry. Materializing a cached file into the working directory (on
`dvc checkout` or right after `dvc add`) uses, in order of preference:
**reflink** (copy-on-write, free and safe where the filesystem supports it),
**hardlink** (free, but the cache file is kept read-only to stop an in-place
edit from silently corrupting every other checkout of that hash),
**symlink**, or a plain **copy** as the always-correct fallback. This choice
has no Git equivalent because Git's blobs are small enough that copying is
free; DVC's often aren't. It's configurable via `dvc config cache.type`.

`cache.dir` relocates the cache itself — to an external drive, or a shared
location several projects reuse. Watch the filesystem boundary when you do:
reflinks and hardlinks can't cross one, so a cache on another volume silently
downgrades every checkout to a real byte copy — full disk I/O, and a second
copy of every version checked out.

!!! warning "A hardlink is not a private copy"
    If the cache type includes `hardlink` and something strips the
    read-only bit and edits the working-directory file in place, that edit
    lands on the cache object too — every other checkout sharing that hash
    (other branches, other clones on the same machine) is now silently
    wrong, since the hash recorded in the `.dvc` file no longer matches the
    bytes at that cache path.

### `.gitignore` is auto-managed, but not auto-staged

`dvc add` also appends an entry to a `.gitignore` **in the same directory**
as the tracked path (`data/.gitignore` gets `/raw.csv`, not a repo-root
entry) — precisely scoped so it can't accidentally ignore an unrelated file
elsewhere in the tree. DVC owns this file: adding more files in that
directory appends more lines, `dvc remove` deletes the matching one.

!!! tip "The step people forget"
    DVC edits `.gitignore` on disk but doesn't stage it. Forgetting
    `git add data/.gitignore` alongside the `.dvc` file means a teammate who
    clones and runs `dvc pull` sees the raw data file show up as untracked
    in `git status` — the ignore rule never made it into the commit.

Pipeline outputs get this treatment automatically — declaring a file under
`outs:` in `dvc.yaml` is enough for `dvc repro` to both cache it and gitignore
it, no separate `dvc add` needed. An `outs` entry with `cache: false` opts
out of both the cache and the ignore rule, leaving the file for Git to track
directly — useful for a small metrics file you want human-diffable in a pull
request.

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

`dvc.yaml` describes a DAG of reproducible stages. Each stage declares its
dependencies explicitly, which is the idea worth internalising: staleness
becomes something DVC *computes* by comparing hashes, not something a
person has to *remember* ("did I retrain after changing the params?"). It's
the same move as a `Makefile` target listing its prerequisites so `make`
computes rebuild-or-skip instead of a person tracking it by hand — and the
same move as a leakage boundary (see
[Data Leakage](concepts/data-leakage.md)'s "structure beats vigilance" tip):
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
way you'd commit `poetry.lock`; `git checkout` an old commit plus
`dvc checkout` restores not just old code but the exact data/param hashes
that made that run reproducible.

`dvc dag` (add `--mermaid` for flowchart syntax) renders the stage graph
read-only from `dvc.yaml`'s declared deps/outs — the pipeline equivalent of
`git log --graph`, useful for spotting a typo'd path that silently leaves a
stage disconnected from the graph instead of erroring.

`dvc metrics diff` / `dvc params diff` compare metrics and hyperparameters
across Git revisions; this overlaps with what an experiment tracker like
[MLflow](mlflow.md) does, but DVC's comparisons are anchored to Git commits
rather than an independent run database.

!!! tip "DVC vs. Git LFS"
    Git Large File Storage (Git LFS) solves the same problem with a similar
    pointer-file trick, but is tied to a specific Git host's LFS server and
    has no pipeline concept. DVC remotes are storage you already have
    (S3, GCS, SSH, …), and `dvc.yaml` pipelines add reproducibility on top of
    plain file versioning.
