# Logging

Python's `logging` stdlib module routes diagnostic messages through a configurable pipeline. Prefer it over `print` for anything beyond a throwaway script: you get severity filtering, multiple output destinations, structured metadata, and zero-code reconfiguration.

## Pipeline

```
Logger → [Filter] → Handler → [Filter] → Formatter → output
```

- **Logger** — the object your code calls; created via `logging.getLogger(__name__)`.
- **Handler** — sends a `LogRecord` somewhere (stream, file, queue, SMTP…).
- **Formatter** — converts a record to a string (or JSON).
- **Filter** — optional accept/reject gate on a logger or handler.

## Logger hierarchy

Loggers are named with dotted paths that mirror Python packages:

```
root → myapp → myapp.services → myapp.services.orders
```

`propagate=True` (default) makes records bubble up to the parent. One `StreamHandler` on root catches everything.

## Levels

| Level    | Value | Use                                           |
|----------|-------|-----------------------------------------------|
| DEBUG    | 10    | Verbose trace; off in production              |
| INFO     | 20    | Normal milestones                             |
| WARNING  | 30    | Unexpected but recoverable (default)          |
| ERROR    | 40    | Failed operation; program continues           |
| CRITICAL | 50    | Fatal                                         |

A record is emitted only when `record.level >= logger.effectiveLevel` **and** `record.level >= handler.level`. Effective level is inherited from the nearest ancestor that has one set.

## Standard module pattern

Every module does only this:

```python
import logging
log = logging.getLogger(__name__)
```

No `basicConfig`, no `addHandler` — that's the application's job.

## Configuration

### `basicConfig` — scripts

```python
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("app.log")],
)
```

No-op if any handler is already on the root logger. Call once, early.

### `dictConfig` — applications

```python
import logging.config

logging.config.dictConfig({
    "version": 1,
    "disable_existing_loggers": False,   # never set True — silences imported loggers
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
        "myapp.db": {"level": "DEBUG"},
        "httpx": {"level": "WARNING"},
    },
})
```

## Library rule

Libraries **never** call `basicConfig` or add handlers. Add only a `NullHandler` to prevent "No handler found" warnings:

```python
# in library __init__.py
logging.getLogger(__name__).addHandler(logging.NullHandler())
```

## Key practices

**`%`-style formatting** — deferred until the record is actually emitted:
```python
log.debug("parsed %d records from %s", n, fname)   # good
log.debug(f"parsed {n} records from {fname}")       # always evaluated
```

**Exceptions with traceback:**
```python
try:
    risky()
except Exception:
    log.exception("risky() failed")   # = log.error(..., exc_info=True)
```

**Structured context via `extra`:**
```python
log.info("order placed", extra={"order_id": 123})
```

**Per-request context with `LoggerAdapter`:**
```python
class ReqAdapter(logging.LoggerAdapter):
    def process(self, msg, kw):
        kw.setdefault("extra", {})["req_id"] = self.extra["req_id"]
        return msg, kw

log = ReqAdapter(logging.getLogger(__name__), {"req_id": req_id})
```

**Async context propagation with `contextvars`** (see [asyncio.md](asyncio.md)):
```python
from contextvars import ContextVar
req_id: ContextVar[str] = ContextVar("req_id", default="-")

class CtxFilter(logging.Filter):
    def filter(self, record):
        record.req_id = req_id.get()
        return True
```

## JSON / structured logging

For log aggregators (Datadog, Loki, CloudWatch):

```bash
pip install python-json-logger
```

```python
from pythonjsonlogger import jsonlogger
handler.setFormatter(jsonlogger.JsonFormatter(
    "%(asctime)s %(name)s %(levelname)s %(message)s"
))
# extra fields are merged into the JSON object
```

Alternative: [`structlog`](../../../tooling/structlog.md) — richer API, keyword-argument style, pluggable renderers.

## Async I/O: QueueHandler + QueueListener

Standard `log.info()` is synchronous — it briefly blocks the event loop. For high-throughput async apps, offload I/O to a thread:

```python
import queue, logging.handlers

q = queue.Queue(-1)
listener = logging.handlers.QueueListener(q, file_handler, respect_handler_level=True)
listener.start()
logging.getLogger().addHandler(logging.handlers.QueueHandler(q))
# listener.stop() at shutdown
```

See [concurrency.md](concurrency.md) for threading context.

## Rotating files

```python
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

RotatingFileHandler("app.log", maxBytes=10_000_000, backupCount=5)
TimedRotatingFileHandler("app.log", when="midnight", backupCount=30)
```

## Setup checklist

1. Entry point only: call `dictConfig` or `basicConfig`.
2. Every module: `log = logging.getLogger(__name__)`.
3. Libraries: `NullHandler` only.
4. `%`-style args in log calls.
5. `log.exception()` inside `except` blocks.
6. Silence noisy deps: `logging.getLogger("httpx").setLevel(logging.WARNING)`.
7. Production: JSON formatter + rotating file or sink.
8. Async + file I/O: `QueueHandler` + `QueueListener`.
