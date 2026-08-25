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

Tab-completion for `git` subcommands, flags, and branch names is a shell feature, not a Git one —
see [command completion](../tools/shell/zsh.md#command-completion).

### Cloning a specific branch

```bash
git clone -b <branch> <url>                 # check out <branch> instead of the default; still fetches all branches
git clone -b <branch> --single-branch <url> # only fetch that branch's history — smaller, faster
git clone --depth 1 -b <branch> <url>       # shallow: latest commit only (--single-branch is implied)
```

- `-b` also accepts a tag name (checks out that tag in detached HEAD).
- Without `--single-branch`, other branches are still downloaded; switch to one later with `git switch <name>`.
- To grab a branch after an ordinary clone: `git fetch origin <branch>` then `git switch <branch>`.

### Deleting a repo

The whole repository — history, branches, config — lives in the hidden `.git` folder. There's no `git` command to delete a repo; it's a plain filesystem operation.

```bash
rm -rf my-project        # delete the whole project, files + history
rm -rf my-project/.git   # "un-git" it: keep files, drop version control
```

- Local only — a repo you pushed still exists on the remote; delete that separately.
- `rm -rf` is irreversible and skips Trash; on a desktop, drag to Trash instead for a recoverable delete.
- `.git` is a dotfile — use `ls -a` to see it.

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

## Referring to commits

Almost every command (`log`, `diff`, `show`, `reset`, `rebase`, `checkout`) takes a *revision* —
any of these forms resolves to a commit SHA:

| Form | Means |
|------|-------|
| `HEAD` (or `@`) | the commit currently checked out |
| `HEAD~` / `HEAD~1` | its parent — one commit back |
| `HEAD~3` | three commits back along the first-parent line |
| `HEAD^` | same as `HEAD~1` (`^` = `^1` = first parent) |
| `HEAD^2` | the **second** parent — only exists on a merge commit |
| `main~2`, `v1.2.0~1` | same arithmetic from any branch or tag, not just `HEAD` |
| `a1b2c3d` | a commit SHA (any unambiguous prefix, usually 7+ chars) |
| `HEAD@{2}` | where `HEAD` pointed 2 moves ago (from the [reflog](undoing.md#recovering-with-reflog)) |
| `main@{yesterday}` | where `main` pointed at that time |

!!! note "`~` walks back, `^` picks a parent"
    On a linear history they're interchangeable: `HEAD~2` == `HEAD^^`. They diverge only at merge
    commits — `~n` always follows the *first* parent n times, while `^n` selects the n-th parent
    of one commit. So `HEAD^2` is "the branch that was merged in", and it's an error on a
    non-merge commit.

Two commits also form ranges:

```bash
git log main..feature      # commits in feature but not in main
git log main...feature     # commits in either but not both (symmetric difference)
git diff HEAD~3 HEAD       # cumulative diff over the last 3 commits
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

### Finding a bug with bisect

`git bisect` binary-searches the commit Directed Acyclic Graph (DAG) for the commit that introduced a regression — O(log n)
checkouts instead of testing every commit.

```bash
git bisect start
git bisect bad                  # current commit is broken
git bisect good v1.2.0            # this older tag/commit was known to work
# Alternatively: git bisect start <bad-sha> <good-sha>
# Git checks out a midpoint commit each round — test it, then:
git bisect good                  # or: git bisect bad
# ... repeats until Git reports the first bad commit ...
git bisect reset                  # return to where you started

git bisect run pytest tests/test_regression.py -x   # automate: exit 0 = good, nonzero = bad
```

!!! note "Merge commits complicate bisect"
    Bisect walks parent pointers, and a merge commit has two — Git has to pick a side to descend
    into. This is why a linear (rebased) history makes bisect simpler; see
    [rebase vs merge](internals.md#rebase-vs-merge-two-ways-to-resolve-the-same-divergence).

## Branching

```bash
git branch                 # list local branches
git branch feature          # create a branch (doesn't switch to it)
git switch feature          # switch to it        (older: git checkout feature)
git switch -c feature        # create + switch in one step  (older: git checkout -b feature)
git branch -d feature        # delete a merged branch
git branch -D feature        # force-delete an unmerged branch
```

Bringing one branch into another — `git merge`, `git rebase`, `git cherry-pick`, and the
interactive rebase used to tidy commits before a pull request — is covered in
[rebasing.md](rebasing.md).

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
- [rebasing.md](rebasing.md) — merging, rebasing, and cherry-picking
- [undoing.md](undoing.md) — `restore`, `reset`, `revert`, reflog recovery, and stashing
- [tags-releases.md](tags-releases.md) — tagging a commit for a release
- [github-actions.md](github-actions.md) — running CI on push/PR
