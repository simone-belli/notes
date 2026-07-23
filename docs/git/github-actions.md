---
quiz: core
---

# GitHub Actions & CI

**Continuous Integration (CI)**: automatically run tests, linters, and type checkers on every push. Failures surface immediately while context is fresh.

**GitHub Actions** is GitHub's built-in CI/CD platform. Workflows are YAML files in `.github/workflows/` that GitHub runs on managed VMs called *runners*.

## Core hierarchy

```
Workflow (.yml file, triggered by events)
└── Job (runs on one runner; jobs run in parallel by default)
    └── Step (a shell command or a reusable Action; steps run sequentially)
```

- **Runner**: a fresh VM (`ubuntu-latest`, etc.) spun up per job.
- **Action**: a reusable step, referenced as `owner/repo@version`.
- **`uses:` vs `run:`**: `uses:` invokes a published Action — generic, reusable infrastructure
  someone else wrote (checkout, language setup, caching). `run:` executes a shell command
  directly — whatever's specific to this project's toolchain (your linter, your test
  command). Pin Actions to a version tag (`@v4`, not `@main`) so an upstream change can't
  silently break your CI.
- Steps in a job run sequentially and **stop at the first non-zero exit** — this is what
  gives a `ruff → mypy → pytest` step sequence fail-fast behavior for free, with no extra
  config needed.

## Minimal Python CI workflow

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]

jobs:
  ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Cache Poetry
        uses: actions/cache@v4
        with:
          path: ~/.cache/pypoetry
          key: ${{ runner.os }}-poetry-${{ hashFiles('poetry.lock') }}

      - run: pip install poetry && poetry install
      - run: poetry run ruff check .
      - run: poetry run mypy .
      - run: poetry run pytest --tb=short
```

## Triggers (`on:`)

| Trigger | When |
|---------|------|
| `push` | Any push (filter with `branches:`, `paths:`) |
| `pull_request` | PR open, sync, reopen |
| `schedule` | Cron: `cron: "0 8 * * 1"` (Mon 8am UTC) |
| `workflow_dispatch` | Manual trigger from the GitHub UI |
| `release` | When a GitHub Release is published |

```yaml
on:
  push:
    branches: [main, "release/**"]
    paths: ["src/**", "tests/**"]   # skip if only docs changed
```

## Job dependencies (sequencing)

Jobs run in parallel unless `needs:` declares a dependency:

```yaml
jobs:
  lint:
    runs-on: ubuntu-latest
    steps: ...

  test:
    needs: lint          # waits for lint to pass
    runs-on: ubuntu-latest
    steps: ...

  deploy:
    needs: [lint, test]
    runs-on: ubuntu-latest
    steps: ...
```

## Secrets and environment variables

```yaml
steps:
  - run: deploy.sh
    env:
      API_KEY: ${{ secrets.MY_API_KEY }}   # from repo Settings → Secrets
      ENV: production
```

`GITHUB_TOKEN` is auto-created per run with permission to push, comment on PRs, etc. — no setup required.

## Matrix builds

Fan out a job across multiple parameter combinations — each combination runs on its own
runner, in parallel, running the job's full step sequence independently:

```yaml
strategy:
  matrix:
    python-version: ["3.12", "3.13"]
steps:
  - uses: actions/setup-python@v5
    with:
      python-version: ${{ matrix.python-version }}
```

- The internal step order (e.g. `ruff → mypy → pytest`) is unaffected — the matrix only
  adds a second dimension (which Python), not a change to how one leg's steps run.
- Each matrix leg becomes a **separate required status check** (e.g. `quality (3.12)`,
  `quality (3.13)`) — select all of them in branch protection, not just one, or the
  unselected version goes unenforced.
- `strategy: fail-fast: false` lets every leg run to completion even if one fails, instead
  of GitHub cancelling the rest the moment any leg fails.

## Caching dependencies

Runners start fresh. Cache to avoid re-installing on every run — either let `setup-python`
manage it (simplest, needs the package manager already on `PATH`):

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: ${{ matrix.python-version }}
    cache: poetry
```

or cache explicitly, which works regardless of install order:

```yaml
- uses: actions/cache@v4
  with:
    path: ~/.cache/pypoetry/virtualenvs
    key: ${{ runner.os }}-poetry-${{ matrix.python-version }}-${{ hashFiles('poetry.lock') }}
```

Cache is invalidated when `poetry.lock` changes (the key's hash component). In a matrix,
include `matrix.python-version` in the key too — different interpreters need separate
virtualenvs (compiled extensions, wheel tags differ), so a shared key would serve the wrong
cache to the wrong version.

## Concurrency: cancelling superseded runs

Without a `concurrency:` block, three quick pushes to the same branch start three full CI
runs that all complete independently, burning runner-minutes on commits nobody cares about
anymore:

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

`group:` scopes what counts as "the same lineage" — `github.ref` keys it per branch/PR so
pushing to one PR doesn't cancel a run on another; `github.workflow` keeps this workflow's
grouping separate from any other workflow using the same ref. `cancel-in-progress: true`
kills the older run in that group the moment a newer one starts. This is a workflow-level
key, placed alongside `on:`, not nested under `jobs:`.

## Artifacts

Share files between jobs or download after a run (kept 90 days):

```yaml
- uses: actions/upload-artifact@v4
  with:
    name: coverage-report
    path: htmlcov/
```

## Useful patterns

!!! note "Workflow files are code — they only change on the next trigger"
    A workflow YAML edit takes effect the next time the triggering event fires. There's no "reload" — if you're debugging a failing push trigger, you must push again after each fix. This also means accidental changes to CI are immediately versioned and revertable via `git revert`.

- **Skip a step conditionally**: `if: github.ref == 'refs/heads/main'`
- **Don't fail on step error**: `continue-on-error: true`
- **Deployment gate**: set `environment: production` on a job → requires manual approval in GitHub UI
- **Workflow files are versioned code** — changes take effect on the next trigger

## Related notes

- [github-repo-governance.md](github-repo-governance.md) — branch protection makes a status check from this workflow a required merge gate
- [git.md](git.md) — branching model that CI enforces
- [testing-strategy.md](../python/tooling/testing/testing-strategy.md) — what CI runs: pytest, coverage
- [ruff.md](../python/tooling/ruff.md) — linter CI runs on every push
- [mypy.md](../python/tooling/mypy.md) — type checker CI runs on every push
- [poetry.md](../python/tooling/poetry.md) — dependency management; `poetry install` in CI