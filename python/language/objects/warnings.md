# Warnings

Warnings are advisory — they print a message and execution continues. Use them for deprecations, non-fatal anomalies, or when you catch an exception but the program can still proceed.

## Basic API

```python
import warnings

warnings.warn("something is off")                         # UserWarning by default
warnings.warn("use new_fn() instead", DeprecationWarning)
```

## Warning hierarchy

```
Warning  (subclass of Exception)
├── UserWarning          ← general user-facing messages
├── DeprecationWarning   ← for developers; hidden in production by default
├── FutureWarning        ← for end-users about changing behaviour
├── RuntimeWarning       ← suspicious runtime behaviour
└── ResourceWarning      ← unclosed files/sockets
```

`Warning` is a subclass of `Exception`, so you can catch warnings with `except Warning` and raise them as exceptions.

## Generating a warning from an exception

Catch the exception, downgrade it to a warning when the program can still proceed:

```python
def load_config(path):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError as e:
        warnings.warn(f"Config not found ({e}), using defaults", UserWarning, stacklevel=2)
        return DEFAULT_CONFIG
```

Pass the exception as the message with `str(e)`, or build a Warning instance directly:

```python
except json.JSONDecodeError as e:
    warnings.warn(f"Malformed JSON at line {e.lineno}: {e.msg}", UserWarning, stacklevel=2)
```

## stacklevel — point at the caller, not your internals

`stacklevel=1` (default) points the warning at the `warn()` call — usually wrong. Use `stacklevel=2` to point at whoever called your function:

```python
def parse(data):
    warnings.warn("bad format", stacklevel=2)  # blame the caller of parse()
```

Increment further if `warn()` is nested inside helpers.

## Warning filters

The same warning (same message + location) is shown only **once** by default.

```python
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("error", category=UserWarning)   # promote to exception
warnings.filterwarnings("always")                        # show every occurrence
```

Temporarily override in a block:

```python
with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    result = old_api()
```

## Custom warning class

```python
class PrecisionWarning(UserWarning):
    """Floating-point precision loss detected."""

warnings.warn("result may lose precision", PrecisionWarning, stacklevel=2)
```

Lets callers filter by type: `warnings.filterwarnings("error", category=PrecisionWarning)`.

## In tests (pytest)

```python
# Assert a warning is emitted:
with pytest.warns(DeprecationWarning, match="use new_fn"):
    old_fn()
```

Promote all warnings to exceptions in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
filterwarnings = ["error"]
```

## Related notes

- [exceptions.md](exceptions.md) — exception hierarchy, raising, chaining, custom exceptions
- [testing-strategy.md](../../tooling/testing-strategy.md) — `pytest.warns` alongside `pytest.raises`
