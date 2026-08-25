# DVC — Workflow

Every DVC (Data Version Control) command has a Git command next to it: DVC
moves the bytes, Git records which bytes. The rhythm is always *DVC first,
Git second* on the way out, and *Git first, DVC second* on the way in.

## One-time setup

```bash
git init && dvc init
dvc remote add -d storage s3://my-bucket/dvc-store
git add .dvc/config .dvcignore && git commit -m "chore: init dvc"
```

Credentials for that remote don't go in the committed file — they belong in
[`.dvc/config.local`](versioning.md#the-local-config-secrets-and-machine-specific-paths),
which is never staged.

## Bringing data under version control

```bash
dvc add data/raw.csv
git add data/raw.csv.dvc data/.gitignore
git commit -m "data: add raw dataset v1"
dvc push                      # bytes to the remote
git push                      # pointers to the Git remote
```

## The daily loop (with a pipeline)

Once [`dvc.yaml`](pipelines.md) exists, `dvc add` is no longer part of the
loop — pipeline outputs are tracked by being declared under `outs:`.

```bash
vim params.yaml               # or the stage script
dvc repro                     # re-runs only the invalidated stages
dvc metrics diff              # working tree vs. HEAD, before committing
git add dvc.yaml dvc.lock metrics.json
git commit -m "feat: raise n_estimators to 500"
dvc push && git push
```

- `dvc status` before committing tells you whether the outputs on disk still
  match `dvc.lock`; `dvc status -c` (cloud) tells you whether the remote is
  missing anything you're about to push.
- Push DVC **before** Git: a pushed pointer whose bytes aren't in the remote
  yet gives a teammate a `dvc pull` failure.

## Joining or resuming a project

```bash
git clone <repo> && cd <repo>
dvc pull                      # fetch bytes for the checked-out pointers
```

## Moving through history

`git checkout` swaps the pointer files; the large files on disk are still
the old ones until DVC is told to follow. (To find out *which* version you're
on or which exist, see
[Reading the data version](versioning.md#reading-the-data-version).)

```bash
git checkout v1.2
dvc checkout                  # working tree now matches the tag
dvc pull                      # only if those hashes aren't in the local cache
```

!!! tip "Let Git run `dvc checkout` for you"
    `dvc install` writes Git hooks so `post-checkout` runs `dvc checkout`,
    `pre-push` runs `dvc push`, and `post-merge` fixes up the working tree.
    Without them the classic failure is silent: branch switched, code new,
    data still the previous branch's — and every number you produce is wrong
    with nothing erroring.

## Comparing experiments

```bash
dvc exp run -S train.n_estimators=500   # run without committing
dvc exp show                            # table of runs, params, metrics
dvc exp branch <exp-name>               # promote a keeper to a real branch
```

`dvc exp run` is `dvc repro` that stashes each result as a lightweight hidden
commit, so a sweep doesn't litter the branch with commits you'll discard.
Overlaps with [Optuna](../experiments/optuna.md) for the search itself and
[MLflow](../experiments/mlflow.md) for the run record — reach for those when
the search strategy or the run database matters more than Git-anchored diffs.

!!! warning "The two-remote mental model"
    A DVC project has two remotes and two histories that must be pushed and
    pulled in step. `git pull` without `dvc pull` (or a `git checkout` without
    `dvc checkout`) leaves code and data from different commits — which is
    exactly the class of bug DVC exists to prevent, reintroduced by skipping
    half the command pair.

## Related

- [Versioning](versioning.md) — what `dvc add` and `dvc push` actually do
- [Pipelines](pipelines.md) — the `dvc.yaml` stages `dvc repro` walks
