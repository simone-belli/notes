# structlog

Third-party logging library that makes structured (key=value) logging the natural default. Every log call produces a dictionary; renderers output it as JSON, coloured console text, or anything else. Sits on top of (or beside) stdlib [`logging`](../language/runtime/logging.md).

## Why over stdlib

- Context binding via `log.bind(key=val)` instead of `LoggerAdapter` / `extra={}`
- Fully composable processor pipeline instead of fixed Filter → Formatter chain
- Built-in `JSONRenderer` and `ConsoleRenderer`
- `capture_logs()` for zero-config test assertions

## Basic usage

```python
import structlog

log = structlog.get_logger(__name__)

log.info("order_placed", order_id=123, user="alice")
# → {"event": "order_placed", "order_id": 123, "user": "alice", ...}
```

## Bound logger

`log.bind(**kw)` returns a new logger with those keys permanently attached:

```python
bound = log.bind(service="pricing", symbol="BTC")
bound.info("price_fetched", price=42.0)
# every future call carries service= and symbol=
```

`log.unbind("symbol")` removes a key. `log.new(**kw)` resets all context.

## Processor pipeline

Each processor is a callable `(logger, method, event_dict) -> event_dict`. They chain in order; the last one renders to a string.

| Processor | Adds |
|-----------|------|
| `add_log_level` | `"level": "info"` |
| `TimeStamper(fmt="iso")` | `"timestamp": "2026-..."` |
| `dict_tracebacks` | exception → nested dict (JSON-safe) |
| `ExceptionRenderer()` | pretty exception in console |
| `merge_contextvars` | pull in async context (see below) |
| `ConsoleRenderer()` | coloured dev output |
| `JSONRenderer()` | JSON string for production |

## Configuration

Call once at startup:

```python
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),          # swap for JSONRenderer() in prod
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    logger_factory=structlog.PrintLoggerFactory(),
)
```

## Async: `contextvars` integration

Attach context to the current async task without threading a bound logger everywhere:

```python
from structlog.contextvars import bind_contextvars, clear_contextvars

async def handle_request(request):
    clear_contextvars()
    bind_contextvars(request_id=request.headers["X-Request-ID"])
    # all log calls in this task (and subtasks) now carry request_id
    log.info("request_received")
```

Requires `merge_contextvars` in the processor chain.

## stdlib integration

Route structlog through stdlib so structlog and `logging.getLogger(...)` share one pipeline:

```python
structlog.configure(
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    processors=[
        ...
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
)

formatter = structlog.stdlib.ProcessorFormatter(processor=structlog.dev.ConsoleRenderer())
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logging.getLogger().addHandler(handler)
```

## Testing

`capture_logs()` replaces the processor chain temporarily and returns all events as a list of dicts:

```python
from structlog.testing import capture_logs

def test_logs_error_on_failure():
    with capture_logs() as cap:
        process_order(order_id=1)

    assert cap[0]["event"] == "processing_failed"
    assert cap[0]["log_level"] == "error"
    assert cap[0]["order_id"] == 1
```

## Install

```bash
pip install structlog
```
