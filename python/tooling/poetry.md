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

Caret semantics follow semver:

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

## Running code

If you `python ...` you use the default environment on your machine. Instead, 
you want to run it using the poetry environment.

```bash
poetry run python -m finlib.module
```

### Sync environment to lock file

```bash
poetry install
```