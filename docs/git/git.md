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
    forward (see the [object model](internals.md#content-addressing-makes-history-tamper-evident)).
    Anyone who already pulled the old commits will get diverged history. Rebase local/unpushed work
    freely; for shared branches, merge instead (or coordinate a force-push).

Merge conflicts leave `<<<<<<<` / `=======` / `>>>>>>>` markers in the affected files — edit them
to the resolved content, then `git add <file>` and `git commit` (merge) or `git rebase --continue`
(rebase).

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

## Stashing

```bash
git stash              # shelve unstaged/staged changes, restore a clean working tree
git stash list          # see shelved stashes
git stash pop            # reapply the most recent stash and drop it
git stash apply          # reapply without dropping it
```

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
