# Git Internals: The Object Model

Every Git command is a thin layer over four object types stored in `.git/objects/` and a few
plain-text pointer files in `.git/refs/`. Git is a content-addressable key-value store with a
directed acyclic graph (DAG) of commits layered on top.

## The four object types

Each object is addressed by the SHA hash of its own content — its hash *is* its ID.

| Type | Contains | Identity |
|------|----------|----------|
| **blob** | raw file bytes | no filename, no path — just content |
| **tree** | a directory listing: `(mode, type, sha, name)` entries pointing to blobs/trees | the structure |
| **commit** | one `tree` hash, parent hash(es) (0, 1, or 2+), author, message | one snapshot + history link |
| **tag** (annotated) | tagger, message, signature, pointer to any other object | a labeled reference, itself an object |

```bash
git cat-file -p <sha>     # pretty-print any object
git cat-file -t <sha>     # show its type: blob | tree | commit | tag
git hash-object -w file   # store file's contents as a blob, print its sha
```

A **lightweight tag** is *not* one of these objects — it's just a ref (see below) that never moves,
same mechanism as a branch. See [tags-releases.md](tags-releases.md) for the practical difference.

!!! note "A commit is a full snapshot, not a diff"
    The tree hash points to the *entire* directory state at that moment. Git computes diffs on
    demand by comparing two trees — it never stores a delta between commits (packfiles compress
    similar objects on disk, but that's a storage optimization, not the data model).

## Content-addressing makes history tamper-evident

This falls directly out of hashing content: change one byte in a nested file → its blob hash
changes → the tree listing it changes hash → every parent tree up to the root changes → the commit
pointing at that root changes hash → every descendant commit (which hashes in its parent's hash)
changes hash too. You can't edit old history in place; `git rebase`/`--amend`/`filter-branch` build
a new object graph from that point forward and move a branch ref to its tip. The old commits remain,
unreferenced, until garbage collected. This is *why* history is tamper-evident — a structural
consequence of content-addressing, not a feature bolted on top.

## Refs: pointers, not objects

Branches, `HEAD`, and lightweight tags live outside the object database as plain text files holding
one commit SHA:

```bash
cat .git/refs/heads/main   # -> 91b2c1a4f9e0...        (a branch: just a commit hash)
cat .git/HEAD              # -> ref: refs/heads/main    (a *symbolic* ref: HEAD names a branch)
```

- **Branch** = a ref under `refs/heads/<name>`. Committing on a branch writes a new commit object,
  then overwrites that one file with the new hash — that's the whole mechanism of "the branch moved
  forward."
- **`HEAD`** normally points at a branch, not directly at a commit — a pointer to a pointer. That
  indirection is why committing on a branch auto-advances it.
- **Detached HEAD**: `HEAD` holds a raw commit SHA instead of `ref: refs/heads/...`. Commits still
  get created, but no branch ref follows them, so they're unreachable (GC-eligible) once you switch
  away — unless a branch is pointed at them first.

## The DAG: parent pointers are the only edges

Blobs and trees form a plain hierarchy with no notion of time. History comes entirely from the
commit object's `parent` field:

- Normal commit → **one** parent (a line).
- Merge commit → **two+** parents (branches joining).
- Root commit → **zero** parents.

It's acyclic by construction: a commit's hash depends on its parent's hash, which must already
exist — so a commit can never become its own ancestor.

```bash
git log --graph --oneline --all    # visualize the DAG across every ref
git merge-base A B                 # nearest common ancestor node
```

!!! tip "One graph, two kinds of file"
    Blobs/trees/commits are immutable once created — hashing content is a pure function. Refs are
    the only mutable piece: cheap plain-text bookmarks pointing at nodes in the graph. `reset`,
    `checkout`, and branch creation just rewrite a ref file; they never touch the object graph
    itself.

## Rebase vs merge: two ways to resolve the same divergence

Once `main` and `feature` have diverged from a common ancestor, there are exactly two ways to
reconcile them, and the object model explains why they behave so differently:

- **Merge** creates one new commit with **two parents** — the tips of both branches. `F`/`G` (the
  original feature commits) are untouched; the DAG now records the true topology: two lines of work
  that rejoined at this point.
- **Rebase** takes each commit unique to `feature` and replays it — same diff — on top of `main`'s
  tip, one at a time. Each replayed commit gets a **different parent** than the original, and since
  a commit's hash is a function of its own tree *and* its parent's hash, a different parent means a
  **different SHA**, even for an identical diff. Rebase doesn't edit `F` into `F'`; objects are
  immutable, so it forges a brand-new object `F'` with the same payload and moves the branch ref to
  point at the new tip. `F`/`G` become unreachable (GC-eligible) the moment nothing points at them.

```
merge:   A---B---C---D---E
                          \
                           H   (parents: [E, G])
                          /
                F--------G

rebase:  A---B---C---D---E---F'---G'
```

This is why **rebasing a commit that anyone else has already pulled is unsafe**: their clone still
has a ref pointing at the old SHA (`F`); yours now points at a different object (`F'`) claiming to
be "the same work." Git has no way to know they're equivalent — content-addressing is exactly what
prevents it from assuming that. A force-push then hands them a diverged history for work they
thought they already had. Rebasing commits nobody else has fetched is completely safe, since no
other ref anywhere can diverge from a SHA that never left your machine — which is also why
throwaway local branches (`git branch -D wip/spike`) are safe to rebase or discard freely.

Neither approach is "more correct" — merge preserves true topology (useful for audit/bisect context
around *when* two lines of work joined); rebase produces a clean, linear line (simpler `git
bisect`, easier to read serially). Which one a team uses is a convention, not a correctness
question — see the command-level warning in [git.md](git.md#merging-and-rebasing).
