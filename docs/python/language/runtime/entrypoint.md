---
tags:
  - cli
  - packaging
quiz: detail
---

# Python Entry Points

## `__name__` and the guard

Every module gets a `__name__` attribute at import time:
- `"__main__"` when the file is **run directly** (`python script.py`)
- The module's dotted name (e.g. `"mypackage.utils"`) when **imported**

The guard exploits this to let a file act as both a script and an importable library:

```python
def main():
    ...

if __name__ == "__main__":
    main()
```

Without the guard, every `import` would execute the top-level code as a side effect. Most tooling (pytest, mypy) imports files — the guard is important even for files you "never plan to import."

`main` is purely conventional — Python enforces nothing about the name.

## `__main__.py` — runnable packages

Add `__main__.py` to a package to make it runnable with `python -m mypackage`:

```
mypackage/
    __init__.py
    __main__.py   ← runs when: python -m mypackage
```

This is how `python -m pytest`, `python -m http.server`, etc. work.

## Async `main`: what changes

!!! warning "Calling async def main() without asyncio.run() silently does nothing"
    `main()` returns a coroutine object. Without `asyncio.run()`, the object is created and immediately discarded — the body never executes. Python emits a `RuntimeWarning: coroutine 'main' was never awaited` but does not raise an exception. The program appears to finish successfully.

Calling `async def main()` returns an inert **coroutine object** — nothing runs:

```python
async def main():
    ...

if __name__ == "__main__":
    main()   # BUG: coroutine object created, not run; RuntimeWarning
```

Use `asyncio.run()` to create an event loop and drive the coroutine to completion:

```python
import asyncio

async def main():
    await some_async_work()

if __name__ == "__main__":
    asyncio.run(main())   # creates loop → runs main() → closes loop
```

`asyncio.run()` always creates a **fresh** loop (no reuse), handles task cleanup, and must be called from synchronous code. Calling it inside an already-running event loop raises `RuntimeError` — inside async code, just `await main()`.

## Console scripts — installed executables

Registering a console script in `pyproject.toml` tells pip to create a real shell
command that calls your `main()` directly.

```toml
# Poetry
[tool.poetry.scripts]
finlib-pipeline = "finlib.pipeline.cli:main"

# Standard (any build backend)
[project.scripts]
finlib-pipeline = "finlib.pipeline.cli:main"
```

The value is `"dotted.module.path:callable"`. Pip generates a wrapper at
`.venv/bin/finlib-pipeline` that imports the module and calls `main()` with no
arguments — so `main()` must read `sys.argv` itself (e.g. via [argparse](../stdlib/cli.md)).

```python
# finlib/pipeline/cli.py
def main() -> None:          # no arguments — pip calls it bare
    parser = argparse.ArgumentParser(...)
    args = parser.parse_args()
    ...

if __name__ == "__main__":   # keep the guard: still works as python cli.py
    main()
```

The return value is passed to `sys.exit()` — return `None` for exit code 0, an int for
anything else.

`poetry install` registers the script immediately in the virtualenv; `pip install
finlib` makes it available globally after packaging.

### Running the script

```bash
poetry run finlib-pipeline          # run inside the venv, no activation needed
poetry run finlib-pipeline --help   # pass arguments the same way
```

`poetry run` is the standard development invocation — it finds the venv automatically
regardless of which directory you're in. Alternatively, activate the shell first:

```bash
poetry shell          # activates the venv in a subshell
finlib-pipeline       # now available directly on PATH
```

!!! tip "Console script vs python -m"
    `python -m finlib.pipeline.cli` works without an install step — use it during
    development. The console script (`finlib-pipeline`) is for end users and deployed
    environments where the package is installed.

## Patterns at a glance

| Scenario | Pattern |
|----------|---------|
| Sync script | `def main()` + `if __name__ == "__main__": main()` |
| Async script | `async def main()` + `if __name__ == "__main__": asyncio.run(main())` |
| Runnable package | `__main__.py` in package |
| Installed shell command | `[tool.poetry.scripts]` / `[project.scripts]` in `pyproject.toml` |
| Test an async entry point | `asyncio.run(main())` in the test body |

## Related

- [asyncio.md](../concurrency/asyncio.md) — event loop, `await`, `gather`, `create_task`
- [cli.md](../stdlib/cli.md) — CLI flags for running Python (`-c`, `-m`)
