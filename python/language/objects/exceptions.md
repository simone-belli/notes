# Exceptions

Python uses exceptions for *all* error conditions — no error codes, no `(value, err)` returns. The happy path stays clean; failures can't be silently ignored.

## EAFP vs LBYL

Python favours **EAFP** (Easier to Ask Forgiveness than Permission): try the operation, handle failure if it occurs.

```python
# LBYL — check first (more Java/C)
if key in d:
    value = d[key]

# EAFP — Pythonic
try:
    value = d[key]
except KeyError:
    value = default
```

EAFP avoids race conditions and is faster when success is the common case.

## Exception hierarchy

```
BaseException
├── SystemExit          ← sys.exit(); do not catch
├── KeyboardInterrupt   ← Ctrl+C; do not catch (or re-raise)
├── GeneratorExit       ← generator .close(); do not catch
└── Exception           ← everything else; your catch boundary
    ├── ValueError      right type, wrong value
    ├── TypeError       wrong type
    ├── AttributeError  obj.attr missing
    ├── KeyError        dict key missing
    ├── IndexError      list index out of range
    ├── FileNotFoundError (subclass of OSError)
    └── RuntimeError    general runtime failure
```

Never catch `BaseException` or bare `except:` — you'll swallow `Ctrl+C` and `sys.exit()`.

## The four clauses

```python
try:
    result = risky_operation()
except ValueError as e:
    handle(e)
except (TypeError, KeyError):
    handle_either()
else:
    # runs only if NO exception was raised
    process(result)
finally:
    # ALWAYS runs — use for cleanup
    cleanup()
```

`else` is underused: it clearly marks "success path" code without accidentally including it inside the error-catching scope.

## Raising exceptions

```python
raise ValueError("quantity must be positive")

# re-raise the current exception with original traceback intact
except ValueError:
    log()
    raise
```

### Exception chaining

Link exceptions to preserve cause when translating between layers:

```python
try:
    data = json.loads(raw)
except json.JSONDecodeError as e:
    raise ValueError("invalid config file") from e   # e becomes __cause__
```

The traceback shows both exceptions. Use `from None` to suppress the original:

```python
raise ValueError("invalid config") from None
```

## Custom exceptions

```python
class AppError(Exception):
    """Base for all application errors."""

class TradeError(AppError):
    """Errors in trade processing."""

class InvalidQuantityError(TradeError):
    def __init__(self, quantity: float):
        self.quantity = quantity
        super().__init__(f"invalid quantity: {quantity}")
```

A hierarchy lets callers catch at the right level (`AppError` vs `TradeError` vs `InvalidQuantityError`) without catching unrelated library exceptions.

## Best practices

- **Be specific** — catch the narrowest type you can actually handle.
- **Don't swallow silently** — at minimum log, then re-raise.
- **Raise at the right level** — low-level code raises specific exceptions; high-level code translates them with `raise X from Y`.
- **Use `finally` for cleanup**, or better: use a [context manager](../runtime/context-managers.md).

```python
# BAD — bug disappears forever
except Exception:
    pass

# GOOD
except Exception:
    logger.exception("process failed")
    raise
```

## Exception attributes

| Attribute | Contents |
|-----------|----------|
| `e.args` | Tuple of constructor arguments |
| `str(e)` | Human-readable message |
| `e.__cause__` | Explicitly chained (`raise X from Y`) |
| `e.__context__` | Implicitly chained (exception during exception handling) |
| `e.__traceback__` | Full traceback object |

## Exceptions and context managers

`__exit__(exc_type, exc_val, exc_tb)` returning `True` suppresses the exception. Use `contextlib.suppress` for this pattern:

```python
from contextlib import suppress

with suppress(FileNotFoundError):
    os.remove("maybe_exists.txt")
```

See [context-managers.md](../runtime/context-managers.md) for the full context manager protocol.

## ExceptionGroup (Python 3.11+)

For concurrent tasks where multiple exceptions can occur simultaneously:

```python
try:
    async with asyncio.TaskGroup() as tg:
        tg.create_task(task_a())
        tg.create_task(task_b())
except* ValueError as eg:    # except* filters by type
    for exc in eg.exceptions:
        print(exc)
```

## Related notes

- [context-managers.md](../runtime/context-managers.md) — context managers (`__exit__` protocol, `@contextmanager`)
- [testing-strategy.md](../../tooling/testing-strategy.md) — `pytest.raises` to assert exceptions in tests
- [pydantic.md](../../tooling/pydantic.md) — `ValidationError` is the canonical custom exception pattern at application boundaries
- [warnings.md](warnings.md) — `warnings.warn()`: downgrade a caught exception to a non-fatal advisory