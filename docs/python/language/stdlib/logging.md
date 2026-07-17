---
tags:
  - logging
quiz: core
---

# Logging (stdlib)

Python's `logging` module routes diagnostic messages through a configurable pipeline. Prefer it over `print`: you get severity filtering, multiple destinations, structured metadata, and zero-code reconfiguration.

## Pipeline

```
Logger → [Filter] → Handler → [Filter] → Formatter → output
```

- **Logger** — the object your code calls; named with dotted paths that mirror the package hierarchy.
- **Handler** — sends records somewhere (stream, file, queue…).
- **Formatter** — converts a record to a string.
- **Filter** — optional accept/reject gate.

## Logger hierarchy

```
root → myapp → myapp.services → myapp.services.orders
```

`propagate=True` (default) makes records bubble up to the parent. A single handler on root catches everything from all descendant loggers.

## Levels

| Level    | Value | Use                              |
|----------|-------|----------------------------------|
| DEBUG    | 10    | Verbose trace; off in production |
| INFO     | 20    | Normal milestones                |
| WARNING  | 30    | Unexpected but recoverable       |
| ERROR    | 40    | Failed operation                 |
| CRITICAL | 50    | Fatal                            |

A record is emitted only when `record.level >= logger.effectiveLevel` **and** `record.level >= handler.level`. Effective level is inherited from the nearest ancestor that has one set.

---

## Library vs application — the fundamental split

| | Library | Application |
|---|---|---|
| Configures logging? | **never** | **yes, once, at startup** |
| Adds handlers? | **never** | yes |
| Calls `basicConfig`? | **never** | optionally |
| Does what instead? | `NullHandler` on its top-level logger | `dictConfig` or `basicConfig` at entry point |

### Library setup

**Every module** — always the same two lines, nothing else:

```python
import logging
log = logging.getLogger(__name__)   # e.g. "mylib.parser"
```

**`__init__.py` only** — add a `NullHandler` to the package root:

```python
import logging
logging.getLogger(__name__).addHandler(logging.NullHandler())
```

`NullHandler` prevents "No handlers could be found for logger `mylib.parser`" warnings when the importing application has not configured logging. It does **not** block propagation — if the application later adds a handler to root, library records flow up to it normally.

!!! warning "Libraries must never call basicConfig or add handlers"
    Calling `basicConfig` in a library silently hijacks the root logger for every application that imports it. `NullHandler` is the only permitted act.

### Application setup

Call `dictConfig` (or `basicConfig`) **once**, at the entry point, before other imports fire:

```python
import logging.config

logging.config.dictConfig({
    "version": 1,
    "disable_existing_loggers": False,     # never True — silences imported loggers
    "formatters": {
        "std": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "std"},
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "std",
            "filename": "app.log",
            "maxBytes": 10_000_000,
            "backupCount": 5,
        },
    },
    "root": {"level": "INFO", "handlers": ["console", "file"]},
    "loggers": {
        "myapp.db": {"level": "DEBUG"},     # verbose for one subtree
        "httpx":    {"level": "WARNING"},   # silence a noisy library
    },
})
```

**`basicConfig`** is simpler and fine for scripts:

```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
```

No-op if any handler is already on root — call it early.

### Where to set the log level

- **Root level** in `dictConfig`/`basicConfig` — floor for the whole app.
- **Per-logger overrides** in `"loggers": {...}` — turn up one module or silence a noisy dep.
- **Never in library code.**

---

## Log call patterns

```python
# %-style args — deferred until record is actually emitted (don't use f-strings)
log.debug("parsed %d records from %s", n, fname)
log.info("order placed: %s", order_id)
log.warning("retry %d/%d for %s", attempt, max, url)

# Exception with traceback (inside except block only)
try:
    risky()
except Exception:
    log.exception("risky() failed")   # = log.error(..., exc_info=True)

# Structured context
log.info("trade executed", extra={"order_id": 123, "symbol": "AAPL"})
```

The lazy `%`-style pattern is logging-specific — [exception](../objects/exceptions.md) messages have no deferred interpolation and must be built eagerly with f-strings.

---

## Key practices

**Per-request context with `LoggerAdapter`:**
```python
class ReqAdapter(logging.LoggerAdapter):
    def process(self, msg, kw):
        kw.setdefault("extra", {})["req_id"] = self.extra["req_id"]
        return msg, kw

log = ReqAdapter(logging.getLogger(__name__), {"req_id": req_id})
```

**Async context propagation with `contextvars`:**
```python
from contextvars import ContextVar
req_id: ContextVar[str] = ContextVar("req_id", default="-")

class CtxFilter(logging.Filter):
    def filter(self, record):
        record.req_id = req_id.get()
        return True
```

**Async I/O — offload file writes to a thread:**
```python
import queue, logging.handlers
q = queue.Queue(-1)
listener = logging.handlers.QueueListener(q, file_handler, respect_handler_level=True)
listener.start()
logging.getLogger().addHandler(logging.handlers.QueueHandler(q))
```

**Rotating files:**
```python
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
RotatingFileHandler("app.log", maxBytes=10_000_000, backupCount=5)
TimedRotatingFileHandler("app.log", when="midnight", backupCount=30)
```

**JSON output** for log aggregators (Datadog, Loki, CloudWatch):
```python
from pythonjsonlogger import jsonlogger
handler.setFormatter(jsonlogger.JsonFormatter(
    "%(asctime)s %(name)s %(levelname)s %(message)s"
))
```

Alternative: [`structlog`](../../libraries/structlog.md) — richer API, keyword-style, pluggable renderers.

---

## Setup checklist

1. **Entry point only**: `dictConfig` or `basicConfig`.
2. **Every module**: `log = logging.getLogger(__name__)`.
3. **Library `__init__.py`**: `NullHandler` only.
4. **Log calls**: `%`-style args, `log.exception()` in `except` blocks.
5. **Silence noisy deps**: `"httpx": {"level": "WARNING"}` in `loggers`.
6. **Production**: JSON formatter + rotating file or queue sink.
