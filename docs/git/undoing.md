---
tags:
  - cli
---

# Git — Undoing Changes

Undoing spans three separate places a change can live: the working tree, the
index, and committed history. Picking the right command is mostly a matter of
knowing which of the three you want to move.

| Situation | Command |
|-----------|---------|
| Discard unstaged edits to a file | `git restore file.py` |
| Unstage a file (keep the edits) | `git restore --staged file.py` |
| Undo the last commit, keep changes staged | `git reset --soft HEAD~1` |
| Undo the last commit, keep changes unstaged | `git reset HEAD~1` |
| Undo the last commit and discard the changes | `git reset --hard HEAD~1` |
| Add a new commit that reverses an old one | `git revert <sha>` |

!!! note "`reset` rewrites history; `revert` adds to it"
    `reset` moves the branch ref backward — safe on local commits, dangerous on pushed ones (same
    reason as [rebase](rebasing.md)). `revert` creates a brand-new commit that undoes another one,
    so it's safe to use on shared/pushed history.

## Recovering with reflog

`reset --hard` only moves the branch ref backward — it doesn't delete the old commits (see
[internals.md](internals.md#content-addressing-makes-history-tamper-evident)). `git reflog` is a
local, chronological log of every place a ref has pointed, independent of the commit graph, so it
can find commits `git log` can no longer reach:

```bash
git reset --hard HEAD~3   # branch ref moves back 3 commits — they vanish from `git log`
git reflog                 # find the commit hash from just before the reset
git reset --hard <hash>    # move the ref back — the 3 commits are visible again
```

!!! tip "The command to remember when you think you've lost work"
    `git reflog` → find the pre-mistake SHA → `git reset --hard <sha>`. Works after a bad rebase,
    an accidental `reset --hard`, or a deleted branch, as long as `git gc` hasn't pruned it yet
    (unreachable objects are kept ~30 days by default).

## Stashing

```bash
git stash              # shelve unstaged/staged changes, restore a clean working tree
git stash -u            # also shelve untracked files
git stash list           # see shelved stashes: stash@{0}, stash@{1}, ...
git stash show -p stash@{0}   # view a stash's diff
git stash pop            # reapply the most recent stash and drop it
git stash apply          # reapply without dropping it
git stash drop stash@{1}      # discard a stash without applying it
git stash branch new-branch stash@{0}   # new branch from the stash's base commit, then apply it
```

`git stash branch` fixes the common failure where `stash pop` conflicts because the branch moved on
since you stashed: it checks out a fresh branch from the stash's original commit first.

## See also

- [git.md](git.md) — the everyday command reference
- [rebasing.md](rebasing.md) — rewriting history deliberately rather than undoing it
