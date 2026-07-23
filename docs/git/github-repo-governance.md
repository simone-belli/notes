---
tags:
  - config
---

# GitHub repo governance

Settings and dotfiles that gate what reaches `main`, beyond what [git.md](git.md) and
[github-actions.md](github-actions.md) cover. On a solo repo the point isn't a second
reviewer — it's a forcing function: a PR gives you a diff view before a change is permanent,
and CI has somewhere to attach a required check.

## Branch protection

**Settings → Branches → Branch protection rules**, targeting `main`:

- **Require a pull request before merging** — disables direct pushes; all changes go through
  a PR. Set required approvals to `0` to allow self-merge on a solo repo — the gate (PR +
  CI) still applies, just without needing someone else's sign-off.
- **Require status checks to pass before merging** — merge is blocked until named CI jobs
  succeed. The check only appears in the picker after the workflow has run at least once.
- **Dismiss stale approvals on new commits** — an approval doesn't carry over to a
  different diff.
- **Require conversation resolution before merging** — no merging over an open review
  thread.

!!! warning "Admins bypass branch protection by default"
    As repo owner you're exempt from these rules unless you also check **"Include
    administrators"**. Without it you can still push straight to `main`.

## `.github/pull_request_template.md`

Auto-fills the PR description box on every new PR — no config beyond the file existing:

```markdown
## What
## Why
## How tested
## Checklist
- [ ] Tests added/updated
- [ ] Docs updated
```

An empty description is easy to skip; a template you only need to edit gets used.

## `.github/CODEOWNERS`

Maps path patterns to reviewers, auto-requested when matching files change in a PR:

```
# .github/CODEOWNERS
*            @yourusername
/finlib/     @yourusername
```

Syntax mirrors `.gitignore` (later, more specific patterns win). Combined with branch
protection's **"Require review from Code Owners"**, it makes the assignment enforced, not
advisory — most useful the moment a second contributor joins.

## Issue templates

`.github/ISSUE_TEMPLATE/*.yml` renders a structured form (dropdowns, required fields)
instead of a blank textarea:

```yaml
# .github/ISSUE_TEMPLATE/todo.yml
name: TODO
description: Track a piece of follow-up work
labels: [todo]
body:
  - type: textarea
    id: description
    attributes:
      label: What needs doing
    validations:
      required: true
```

Labels (**Issues → Labels**) classify issues and are what a template's `labels:` field
pre-applies — a `todo` label makes a backlog item filterable later
(`is:issue is:open label:todo`).

!!! tip "How the pieces click together"
    Branch protection makes a PR mandatory → the PR template gives it context → CODEOWNERS
    makes review assignment automatic → a required CI status check is the actual gate, not
    just a formality. Self-merge with 0 required approvals keeps the loop fast solo, but
    with a paper trail instead of a raw push to `main`.

## Related notes

- [github-actions.md](github-actions.md) — CI workflow that a required status check runs
- [git.md](git.md) — branching model this process wraps around
