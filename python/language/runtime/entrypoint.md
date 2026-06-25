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

## Patterns at a glance

| Scenario | Pattern |
|----------|---------|
| Sync script | `def main()` + `if __name__ == "__main__": main()` |
| Async script | `async def main()` + `if __name__ == "__main__": asyncio.run(main())` |
| Runnable package | `__main__.py` in package |
| Test an async entry point | `asyncio.run(main())` in the test body |

## Related

- [asyncio.md](asyncio.md) — event loop, `await`, `gather`, `create_task`
- [cli.md](cli.md) — CLI flags for running Python (`-c`, `-m`)
