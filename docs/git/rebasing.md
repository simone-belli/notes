---
tags:
  - cli
---

# Git — Rebasing

Merge and rebase both integrate one line of work into another; they differ in
whether history is preserved or rewritten. Rebase replays commits onto a new
base, producing new SHAs — which is what makes it powerful for cleanup and
dangerous on shared branches.

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

## Interactive rebase: cleaning up commits

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
[Conventional Commit](tags-releases.md#conventional-commits) message.

```bash
git rebase --continue   # after resolving a conflict + git add
git rebase --abort       # bail out, restore the pre-rebase state
```

The argument is the **base** — the commit *below* the ones you want to edit, which is itself left
untouched:

```bash
git rebase -i HEAD~5      # edit the last 5 commits
git rebase -i a1b2c3d~1   # edit a1b2c3d and everything after it
git rebase -i --root       # include the very first commit (which has no parent)
```

Use `edit` as the verb to stop *at* a commit: Git replays up to it and hands back the working tree,
so you can amend the content, not just the message.

```bash
git rebase -i HEAD~3      # mark the target line `edit`
# ... change files ...
git add .
git commit --amend        # rewrite that commit in place
git rebase --continue      # replay the commits that came after it
```

## Rebasing onto a different base

`git rebase --onto <newbase> <upstream> [<branch>]` moves the commits in `<upstream>..<branch>`
onto `<newbase>` — the explicit three-argument form when "replay my branch onto main" isn't what
you want.

```bash
git rebase --onto main feature~3           # replay only feature's last 3 commits onto main
git rebase --onto main old-parent feature   # move feature off old-parent and onto main
git rebase --onto HEAD~2 HEAD~1             # drop HEAD~1 from history, keeping HEAD
```

With two arguments `<branch>` defaults to the current one, so `--onto HEAD~2 HEAD~1` replays the
range `HEAD~1..HEAD` (just the tip commit) onto `HEAD~2` — deleting one commit from the middle of
local history without opening the interactive editor.

## Cherry-picking a single commit

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

## See also

- [git.md](git.md) — the everyday command reference
- [undoing.md](undoing.md) — `reset`, `revert`, and recovering a botched rebase with the reflog
- [internals.md](internals.md) — why replaying commits necessarily changes their SHAs
