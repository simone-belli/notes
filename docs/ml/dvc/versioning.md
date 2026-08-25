# DVC — Versioning

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
[Git Internals: The Object Model](../../git/internals.md)), just with one more
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
`outs:` in `dvc.yaml` is enough for [`dvc repro`](pipelines.md) to both cache
it and gitignore it, no separate `dvc add` needed. An `outs` entry with
`cache: false` opts out of both the cache and the ignore rule, leaving the
file for Git to track directly — useful for a small metrics file you want
human-diffable in a pull request.

## Reading the data version

DVC has no version numbers. A dataset's version is a **pair**: the content hash (which
bytes) and the Git revision containing that pointer (which bytes *together with which
code*). Both are already in the repo:

```bash
cat data/raw.csv.dvc                      # the md5 of what's checked out
git rev-parse HEAD                        # the revision pinning it
git log --oneline -- data/raw.csv.dvc     # every version this file has had
```

`git log` on the pointer file is the closest thing to a version *list* — one commit per
change — and each entry is checkout-able:

```bash
git checkout <commit> -- data/raw.csv.dvc
dvc checkout data/raw.csv
```

Pipeline outputs have no `.dvc` file; their hashes live in [`dvc.lock`](pipelines.md) under
the producing stage's `outs:`, and the same `git log` reasoning applies to that file.

- `dvc status` — do the files on disk still match the recorded hashes?
- `dvc data status` — Git-status-style view (`not_in_cache`, `modified`, `uncommitted`).
- `dvc diff <rev> <rev>` — which paths and hashes changed between two versions; compares
  hash and size, never line content.

!!! tip "Give versions human names with Git tags"
    `git tag -a data-v2` after committing the pointer, and `dvc diff data-v1 data-v2` or
    `git checkout data-v2 && dvc checkout` read the way people expect versions to read —
    without DVC needing a version concept of its own.

### From Python

```python
import dvc.api

url = dvc.api.get_url("data/raw.csv", rev="v1.0")     # its location in the remote

with dvc.api.open("data/raw.csv", rev="v1.0") as f:   # stream a past version
    ...
```

`rev=` takes anything Git resolves (tag, branch, commit hash) and leaves the working tree
untouched — safe to call from inside a training script. The hash itself is plain YAML:

```python
import yaml
from pathlib import Path

md5 = yaml.safe_load(Path("data/raw.csv.dvc").read_text())["outs"][0]["md5"]
```

!!! tip "Log both halves with every run"
    Record the Git commit *and* the data hash next to each result. That pair is the
    difference between reproducing a number months later and guessing at it — see
    [Reproducibility](../concepts/reproducibility.md).

### Imported data

`dvc import` records the source *and* the revision it resolved to, so a moving branch name
can't silently change your inputs:

```yaml
deps:
- path: data/raw.csv
  repo:
    url: https://github.com/example/datasets
    rev: main            # what was asked for
    rev_lock: 6a5b7f2c…  # what was pinned
```

`dvc update data/raw.csv.dvc` re-resolves `rev` and moves `rev_lock` forward — a deliberate
act, not a side effect of someone else pushing.

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

### The local config: secrets and machine-specific paths

`.dvc/config` is committed, so anything secret or machine-specific belongs in
`.dvc/config.local` instead — same format, same keys, written by adding
`--local` to the command, and gitignored by `dvc init` from the start.

```bash
dvc config --local cache.dir /mnt/big-disk/dvc-cache
dvc remote modify --local storage access_key_id <key>
dvc remote modify --local storage secret_access_key <secret>
```

- Four levels, each overriding the previous: `--system` → `--global`
  (per-user, `~/.config/dvc/config`) → `--project` (the default,
  `.dvc/config`, committed) → `--local` (`.dvc/config.local`, ignored).
- The split is what lets the committed config carry the remote's *URL* —
  the part every clone needs — while each clone supplies its own credentials
  and cache location for the same remote name.
- `dvc config --list` prints the merged result; add a level flag to see one
  layer alone, or `--show-origin` to see which file each value came from.

!!! tip "Reach for `--local` before inventing a workaround"
    A shared cache on an external drive, a colleague's read-only remote, a
    different default remote on the training box — these look like they need
    a config change everyone will inherit, but they're exactly what the local
    layer is for. Editing `.dvc/config` instead either commits a path that
    only exists on one machine, or leaks a key into Git history.

!!! tip "DVC vs. Git LFS"
    Git Large File Storage (Git LFS) solves the same problem with a similar
    pointer-file trick, but is tied to a specific Git host's LFS server and
    has no pipeline concept. DVC remotes are storage you already have
    (S3, GCS, SSH, …), and [`dvc.yaml` pipelines](pipelines.md) add
    reproducibility on top of plain file versioning.

## Related

- [Pipelines](pipelines.md) — turning tracked files into a reproducible DAG
- [Workflow](workflow.md) — the day-to-day command sequence
- [Reproducibility](../concepts/reproducibility.md) — why any of this matters
