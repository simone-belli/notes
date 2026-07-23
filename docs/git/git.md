---
tags:
  - cli
---

# Git — Command Reference

Git is a distributed version control system used to track changes in code and collaborate safely.
Under the hood, commits, branches, and history are all built from a small [object model](internals.md).

## Setup

```bash
git init                                    # create a repo in the current directory
git clone <url>                             # copy a remote repo locally

git config --global user.name "Name"
git config --global user.email "you@example.com"
git config --global init.defaultBranch main
git config --global alias.st status         # usage: git st
```

## Typical workflow

```bash
git status                  # what's changed / staged
git add file.py              # stage one file
git add .                    # stage everything in and below the cwd
git commit -m "message"      # snapshot the staged changes
git log --oneline            # compact history
git remote add origin <url>  # connect a remote once
git push -u origin main       # first push: also sets the upstream branch
git pull                      # fetch + merge from the tracked upstream
```

## Inspecting changes

```bash
git diff                 # unstaged changes vs the last commit
git diff --staged        # staged changes vs the last commit
git diff main..feature   # changes between two branches
git add -p               # stage a file interactively, hunk by hunk
git show <sha>            # full diff + metadata for one commit
git log --oneline --graph --all   # visualize branches and merges
git blame file.py          # who last touched each line, and in which commit
```

## Branching

```bash
git branch                 # list local branches
git branch feature          # create a branch (doesn't switch to it)
git switch feature          # switch to it        (older: git checkout feature)
git switch -c feature        # create + switch in one step  (older: git checkout -b feature)
git branch -d feature        # delete a merged branch
git branch -D feature        # force-delete an unmerged branch
```

## Merging and rebasing

```bash
git merge feature           # bring feature's commits into the current branch
                              # (fast-forward if possible, else a merge commit)
git rebase main              # replay the current branch's commits onto main's tip
```

!!! warning "Never rebase commits that are already pushed and shared"
    Rebase rewrites commits — new SHAs — because it builds a new object graph from that point
    forward (see [rebase vs merge](internals.md#rebase-vs-merge-two-ways-to-resolve-the-same-divergence)).
    Anyone who already pulled the old commits will get diverged history. Rebase local/unpushed work
    freely; for shared branches, merge instead (or coordinate a force-push).

Merge conflicts leave `<<<<<<<` / `=======` / `>>>>>>>` markers in the affected files — edit them
to the resolved content, then `git add <file>` and `git commit` (merge) or `git rebase --continue`
(rebase).

### Interactive rebase: cleaning up commits

`git rebase -i HEAD~5` opens an editor listing the last 5 commits (oldest first); editing the verb
and the line order is the whole interface.

| Verb | Effect |
|------|--------|
| `pick` | keep as-is |
| `reword` | keep the diff, edit the message |
| `squash` | combine into the previous commit, merge both messages |
| `fixup` | combine into the previous commit, discard this message |
| `drop` (or delete the line) | discard the commit entirely |

```
pick a1b2c3d wip
fixup e4f5g6h fix typo
fixup h7i8j9k more wip
reword k1l2m3n feat: add user auth endpoint
```
Squashes 4 messy commits into 1, using `reword` to write a single clean
[Conventional Commit](https://www.conventionalcommits.org/) message.

```bash
git rebase --continue   # after resolving a conflict + git add
git rebase --abort       # bail out, restore the pre-rebase state
```

### Cherry-picking a single commit

`git cherry-pick <hash>` replays one commit's diff onto the current branch as a **new** commit —
same idea as rebase, but for one hand-picked commit instead of a whole range (new parent → new SHA).
Typical use: a hotfix on `main` needs to land on `release/1.2` too, without pulling in main's other
unrelated commits.

```bash
git cherry-pick abc123        # apply abc123's diff onto HEAD as a new commit
git cherry-pick -n abc123      # apply + stage, but don't commit yet
git cherry-pick --continue     # after resolving a conflict
git cherry-pick --abort         # bail out
```

## Undoing changes

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
    reason as rebase above). `revert` creates a brand-new commit that undoes another one, so it's
    safe to use on shared/pushed history.

### Recovering with reflog

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

## Ignoring files

```bash
# .gitignore
*.log
__pycache__/
.env
```

```bash
git rm --cached secrets.env   # stop tracking a file without deleting it from disk
```

## See also

- [internals.md](internals.md) — what a commit/branch actually *is* under the hood
- [tags-releases.md](tags-releases.md) — tagging a commit for a release
- [github-actions.md](github-actions.md) — running CI on push/PR
