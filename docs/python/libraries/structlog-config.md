---
tags:
  - logging
  - config
---

# structlog — Configuration

Everything structlog does to an event dictionary is a processor, and
`structlog.configure()` is where the chain is assembled. Configure **once at
the entry point**, never in library code — see
[structlog.md](structlog.md) for the calling API this sits behind.

## Processor pipeline

Each processor is a callable `(logger, method, event_dict) -> event_dict`. They chain in order; the last one renders to a string.

| Processor | Adds |
|-----------|------|
| `add_log_level` | `"level": "info"` |
| `TimeStamper(fmt="iso")` | `"timestamp": "2026-..."` |
| `dict_tracebacks` | exception → nested dict (JSON-safe) |
| `ExceptionRenderer()` | pretty exception in console |
| `merge_contextvars` | pull in async context |
| `ConsoleRenderer()` | coloured dev output |
| `JSONRenderer()` | JSON string for production |

## `structlog.configure()`

```python
import structlog

structlog.configure(
    processors=[...],       # pipeline: list of (logger, method, event_dict) → event_dict
    wrapper_class=...,      # what get_logger() returns
    logger_factory=...,     # what performs final I/O
    context_class=dict,     # storage for bound context
)
```

### Native mode (structlog owns I/O)

structlog writes to stdout directly. Use when you don't need to share a pipeline with stdlib libraries.

```python
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,   # must be first
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),            # dev; swap for JSONRenderer() in prod
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    logger_factory=structlog.PrintLoggerFactory(),
)
```

### stdlib mode (shared pipeline with third-party libraries)

structlog preprocesses; stdlib handlers do the routing (file, SMTP, etc.). Third-party `logging.getLogger()` calls and structlog calls share one renderer.

```python
# 1. structlog hands off to stdlib
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,  # must be last
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

# 2. stdlib renders what structlog sends
formatter = structlog.stdlib.ProcessorFormatter(
    processor=structlog.dev.ConsoleRenderer(),
    foreign_pre_chain=[                       # handles logs from stdlib loggers (httpx, etc.)
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ],
)
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logging.getLogger().addHandler(handler)
logging.getLogger().setLevel(logging.INFO)
```

!!! note "foreign_pre_chain is required in stdlib mode"
    Records arriving from stdlib loggers (e.g. httpx, sqlalchemy) have no `event` key. `foreign_pre_chain` preprocesses them before the formatter runs. Without it, those records error.

### Switching renderer via Settings

The renderer is just the last item in the `processors` list — pick it with a plain conditional on a [pydantic Settings](pydantic/pydantic-settings.md) field:

```python
shared_processors = [
    structlog.contextvars.merge_contextvars,
    structlog.processors.add_log_level,
    structlog.processors.TimeStamper(fmt="iso"),
]
renderer = (
    structlog.processors.JSONRenderer()
    if settings.environment == "production"
    else structlog.dev.ConsoleRenderer()
)
structlog.configure(processors=[*shared_processors, renderer], ...)
```

Keeping `shared_processors` common to both branches means only the *encoding* changes between environments, not the log content.

### Dev vs prod processor chain

| Processor | Dev | Prod |
|---|---|---|
| `merge_contextvars` | yes | yes |
| `add_log_level` | yes | yes |
| `TimeStamper(fmt="iso")` | yes | yes |
| `ExceptionRenderer()` | yes — pretty console | — |
| `dict_tracebacks` | — | yes — exceptions as JSON-safe dict |
| `ConsoleRenderer()` | yes | — |
| `JSONRenderer()` | — | yes |

### `wrapper_class` and `logger_factory`

| Parameter | Native mode | stdlib mode |
|---|---|---|
| `wrapper_class` | `make_filtering_bound_logger(logging.INFO)` — level baked in, zero-cost filtering | `structlog.stdlib.BoundLogger` |
| `logger_factory` | `PrintLoggerFactory()` | `stdlib.LoggerFactory()` |

## See also

- [structlog.md](structlog.md) — log calls, bound loggers, `contextvars`
- [logging.md](../language/stdlib/logging.md) — the stdlib pipeline stdlib mode plugs into
