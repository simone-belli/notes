---
tags:
  - packaging
quiz: detail
---

# Poetry

## What is Poetry?

Poetry is a modern Python tool for:

- dependency management
- virtual environment management
- packaging Python projects

It replaces the traditional combination of:

- `pip`
- `requirements.txt`
- `virtualenv`
- `setup.py`

with a single workflow centered around:

- `pyproject.toml` (requirements)
- `poetry.lock` (what's installed)

It provides a unified workflow for managing Python projects.

---

## Why use Poetry?

Main advantages:

- reproducible environments
- deterministic dependency versions
- automatic virtual environments
- cleaner project structure
- easier collaboration

Poetry helps avoid:
> "works on my machine" problems.

---

## Installation (macOS)

Install Poetry:

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

---

## Project scaffold

```bash
poetry new finlib
cd finlib
poetry add pydantic
poetry add --group dev mypy ruff black pytest
```

```text 
finlib/
|-- pyproject.toml
|-- src/finlib/__init__.py
|-- tests/
```

---

## `poetry add`

`poetry add <package>` declares a new dependency. It does four things atomically:

1. Resolves the package against existing constraints
2. Updates `pyproject.toml` with a version constraint
3. Updates `poetry.lock` with exact pinned versions for all packages
4. Installs into the virtual environment

!!! note "Two files, two jobs: pyproject.toml is the intention; poetry.lock is the truth"
    `pyproject.toml` records human-readable constraints (`^2.31.0`). `poetry.lock` records the exact resolved version of every dependency and transitive dependency. Commit both: `pyproject.toml` so humans can read the constraints; `poetry.lock` so `poetry install` on another machine produces an identical environment. Never hand-edit `poetry.lock`.

**The two files:**

```
pyproject.toml   ← human-edited constraints ("what I want")
poetry.lock      ← machine-generated exact pins ("what's installed")
```

Commit both. Never hand-edit `poetry.lock`.

### Version constraints

By default, Poetry writes a **caret constraint** (`^`):

```bash
poetry add requests    # writes requests = "^2.31.0" in pyproject.toml
```

Caret semantics follow [semver](../../tools/semver.md):

| Constraint | Resolves to          | Reasoning                           |
|------------|----------------------|-------------------------------------|
| `^1.2.3`   | `>=1.2.3, <2.0.0`   | Major locked                        |
| `^0.2.3`   | `>=0.2.3, <0.3.0`   | Major=0 → minor locked              |
| `^0.0.3`   | `>=0.0.3, <0.0.4`   | Major=minor=0 → patch locked        |

Other operators: `~` (lock major+minor), `>=`, `==` (exact pin), `!=` (exclude).

### Dependency groups

Groups separate runtime from dev/test dependencies:

```bash
poetry add --group dev pytest ruff mypy      # excluded from prod installs
poetry add --group test factory-boy faker
```

`poetry install --without dev` skips dev groups. The old `--dev` flag is deprecated.

### Extras

```bash
poetry add "uvicorn[standard]"    # optional sub-deps bundled by the package
```

### Useful flags

```bash
poetry add --dry-run requests     # preview changes without acting
poetry add --lock requests        # update files only, skip install
poetry add git+https://github.com/org/repo.git#tag   # git source
poetry add ../local-pkg --editable                   # local editable path
```

### add vs install vs update

| Command          | pyproject.toml? | poetry.lock?       | Installs? |
|------------------|-----------------|-------------------|-----------|
| `poetry add`     | Yes (new dep)   | Yes (re-resolves) | Yes       |
| `poetry install` | No              | No (reads it)     | Yes       |
| `poetry update`  | No              | Yes (re-resolves) | Yes       |
| `poetry remove`  | Yes (removes)   | Yes               | Yes (removes) |

`poetry install` is idempotent — makes the environment match the lock file exactly.

---

## Console scripts

Register a shell command that pip installs into the environment's `bin/`:

```toml
[tool.poetry.scripts]
finlib-pipeline = "finlib.pipeline.cli:main"
```

Value format: `"dotted.module:callable"`. See [entrypoint.md](../language/runtime/entrypoint.md) for how to write `main()` and how this compares to `python -m`.

---

## Running code

If you `python ...` you use the default environment on your machine. Instead, 
you want to run it using the poetry environment.

```bash
poetry run python -m finlib.module
```

---

## `poetry install`

Syncs the virtual environment to the project's declared dependencies — the "set up / reproduce my environment" command you run after cloning a repo or pulling changes. What it does:

1. **Finds or creates** the project's virtualenv (creates one if none exists).
2. **Decides whether to resolve**, by comparing `poetry.lock` to `pyproject.toml` via a content hash:
   - lock **fresh** → install the exact pins straight from the lock, no resolution (fast, deterministic);
   - lock **missing** → resolve from `pyproject.toml` and write a fresh `poetry.lock` first;
   - lock **stale** (hand-edited `pyproject.toml`) → warns to run `poetry lock`, installs from the lock anyway.
3. **Installs only the delta** — already-correct packages are untouched (idempotent).
4. **Installs the root project itself** in editable mode (like `pip install -e .`), unless `--no-root`.

!!! note "`install` obeys the lock; `update` rewrites it"
    `poetry install` treats `poetry.lock` as the source of truth and never changes the pins — it only makes the environment reflect them. `poetry update` re-resolves within the `pyproject.toml` constraints, bumps to newer allowed versions, and rewrites the lock. `install` is the *consumer* of reproducibility; `add`/`update`/`lock` are the *producers*. A committed lock means every `poetry install` yields an identical environment.

### Scope flags

```bash
poetry install                     # full dev environment (main + non-optional groups + root)
poetry install --without dev       # runtime deps only (replaces deprecated --no-dev)
poetry install --with docs         # include an optional group that's off by default
poetry install --only main --no-root   # lean prod: no dev tools, don't install the app
poetry install --sync              # prune packages present in the venv but not in the lock
```

- Default installs **main** deps + all **non-optional** [groups](#dependency-groups) + the root package.
- `--no-root` — install dependencies but not the project itself (Docker layer caching: copy `pyproject.toml`/`poetry.lock`, `install --no-root`, then copy source; also for non-package apps).
- `--sync` — make the env *exactly* the lock (removes strays); plain `install` only **adds**. (Older Poetry: `--remove-untracked`; Poetry 2.x also has `poetry sync`.)
- `--extras "name"` / `--all-extras` — include the project's optional extras; `--dry-run` previews.

!!! warning "It never updates versions"
    A released newer version won't be picked up — the lock still pins the old one. Use [`poetry update`](#add-vs-install-vs-update) (or `poetry add pkg@latest`). And `install` only sets the env up; run code through it with `poetry run …`.