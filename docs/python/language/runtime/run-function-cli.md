---
tags:
  - cli
---

# Running a Function from the Shell

Every way of calling a function from the command line does the same two things — import
the module, call a callable — and differs only in who writes the glue. Pick by how
permanent the invocation is.

| Mechanism | You write | Use for |
|---|---|---|
| `python -c "from pkg.mod import fn; fn()"` | nothing | one-off, throwaway |
| `python script.py` | a `__main__` guard | standalone script, no relative imports |
| `python -m pkg.mod` | a `__main__` guard | a command inside a package |
| `python -m pkg` | a `__main__.py` | the package has one obvious action |
| `mytool` (console script) | `[project.scripts]` entry | a command end users run |

The last three are covered in [entrypoint.md](entrypoint.md); this page covers the ad-hoc
ones and the mechanics that decide which works.

## `python -c` — no cooperation needed

`-c` executes a source string as `__main__`. It is the only form that needs nothing from
the target module — no guard, no entry point, no parser:

```bash
python -c "from mypkg.stats import sharpe; print(sharpe(window=7))"
```

Trailing arguments land in `sys.argv`, with `sys.argv[0] == "-c"`:

```bash
python -c "import sys; print(sys.argv)" a b     # ['-c', 'a', 'b']
```

Compound statements (`for`, `if`, `def`) need real newlines. Feed them on standard input
with `python -` instead of fighting shell quoting:

```bash
python - <<'PY'
from mypkg.stats import sharpe
for w in (7, 30, 90):
    print(w, sharpe(window=w))
PY
```

!!! tip "`-c` is a scriptable interpreter session"
    Use it to poke at an installed package, sanity-check a function in a Makefile, or debug
    an import. The moment it needs newlines or argument parsing, write a module and run it
    with `-m`.

## `python -m pkg.mod` vs `python pkg/mod.py`

These are not interchangeable. They differ in what goes on `sys.path` and whether the
module knows its package.

| | `python pkg/mod.py` | `python -m pkg.mod` |
|---|---|---|
| Prepended to `sys.path` | the **script's** directory | the **current working** directory |
| `__package__` | `""` | `"pkg"` |
| Relative imports | fail | work |
| `pkg/__init__.py` runs | no | yes |

```python
# mypkg/report.py
from .stats import sharpe          # relative import
```

```bash
python mypkg/report.py     # ImportError: attempted relative import with no known parent package
python -m mypkg.report     # works
```

!!! warning "Run package modules with `-m`, always"
    `python pkg/mod.py` executes the file as if it were loose on disk, so `from .x import y`
    has no parent package to resolve against. See
    [import-system.md](import-system.md#absolute-vs-relative-imports).

`-m` requires the module to be *importable*: either the working directory is the project
root, or the package is installed (`poetry install`, `pip install -e .`). A
`ModuleNotFoundError` from `-m` is nearly always a wrong-directory problem, not a code one.

!!! note "`-m` can execute a module twice"
    `python -m mypkg.report` creates a `__main__` module object; if anything else does
    `import mypkg.report`, a *second*, separate module object exists. Module-level state
    (caches, registries) then lives twice. Keep the runnable module thin — parse arguments,
    call functions defined elsewhere.

## Getting arguments in

Every mechanism except `-c` lands on a zero-argument `main()` that must turn `sys.argv`
into function arguments. Keep `main` thin so the real function stays testable:

```python
import argparse
from mypkg.stats import sharpe

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--window", type=int, default=30)
    args = parser.parse_args()
    print(sharpe(window=args.window))     # real work takes plain arguments

if __name__ == "__main__":
    main()
```

See [cli.md](../stdlib/cli.md) for the full `argparse` reference, including
[lists and structured values](../stdlib/cli.md#lists) (`nargs`, `action="append"`,
`type=json.loads`).

### Dispatching to one of several functions

`set_defaults(func=...)` stores the function object in the namespace, so `main` never grows
an `if`/`elif` chain:

```python
def cmd_fetch(args: argparse.Namespace) -> None: ...
def cmd_report(args: argparse.Namespace) -> None: ...

sub = parser.add_subparsers(required=True)

p_fetch = sub.add_parser("fetch")
p_fetch.add_argument("--symbol")
p_fetch.set_defaults(func=cmd_fetch)

sub.add_parser("report").set_defaults(func=cmd_report)

args = parser.parse_args()
args.func(args)          # dispatch
```

Adding a command means adding a parser and a function — the dispatch line never changes.

### Deriving the interface from the signature

Third-party libraries build the parser from type hints instead. **Typer** (built on Click):

```python
import typer

app = typer.Typer()

@app.command()
def sharpe(window: int = 30, verbose: bool = False) -> None:
    ...

if __name__ == "__main__":
    app()
```

`--window 7 --verbose`, `--help`, and type coercion all come from the annotations.
**Fire** needs no decorator and can expose an existing module as-is:

```bash
python -m fire mypkg.stats sharpe --window 7
```

Zero changes to the module — excellent for internal tooling, poor for a shipped interface,
since the command surface is whatever the module happens to contain.

## `runpy` — `-m` from inside Python

```python
import runpy

runpy.run_module("mypkg.report", run_name="__main__")   # what python -m does
runpy.run_path("scripts/one_off.py", run_name="__main__")
```

Both return the resulting module globals as a dict. Useful in build scripts; for testing a
command-line entry point, calling `main()` with a patched `sys.argv` is cleaner.

## Failure modes

| Symptom | Cause | Fix |
|---|---|---|
| `attempted relative import with no known parent package` | ran `python pkg/mod.py` | `python -m pkg.mod` |
| `ModuleNotFoundError: No module named 'mypkg'` under `-m` | wrong directory, or not installed | `cd` to project root, or `pip install -e .` |
| Module runs, nothing happens | no `__main__` guard, or `main()` never called | add `if __name__ == "__main__": main()` |
| `RuntimeWarning: coroutine 'main' was never awaited` | `async def main()` called bare | `asyncio.run(main())` |
| Wrong interpreter or missing dependency | virtual environment not active | prefix with `poetry run` |

## Related

- [entrypoint.md](entrypoint.md) — `__main__` guard, `__main__.py`, console scripts
- [cli.md](../stdlib/cli.md) — `sys.argv`, argparse, testing entry points
- [import-system.md](import-system.md) — `sys.path`, packages, relative imports
- [poetry.md](../../tooling/poetry.md) — `poetry run`, virtual environments
