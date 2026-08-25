---
tags:
  - logging
quiz: detail
---

# structlog

Third-party logging library that makes structured (key=value) logging the natural default. Every log call produces a dictionary; renderers output it as JSON, coloured console text, or anything else. Sits on top of (or beside) stdlib [`logging`](../language/stdlib/logging.md).

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

## stdlib vs structlog: when to use which

!!! warning "Libraries must always use stdlib"
    A library that imports structlog forces consumers to install and configure it. Libraries call `logging.getLogger(__name__)` only — configuration belongs to the application.

| Situation | Use |
|---|---|
| Script / CLI tool | stdlib — `basicConfig` is one line |
| Library / reusable package | stdlib — always |
| Service / API / async app | structlog |
| Per-request context (`request_id`, `trace_id`) without `extra={}` boilerplate | structlog (`bind_contextvars`) |
| JSON output for log aggregator | structlog or stdlib + `python-json-logger` |
| Simple test assertions on log output | structlog (`capture_logs()`) |
| Need `RotatingFileHandler`, `SMTPHandler`, external `dictConfig` file | stdlib |

They also compose: structlog can sit on top of stdlib ([stdlib mode](structlog-config.md#stdlib-mode-shared-pipeline-with-third-party-libraries)), so third-party libs using `logging.getLogger` route through the same handler as your structlog calls.

## Log methods

| Method | Level | Notes |
|---|---|---|
| `log.debug(event, **kw)` | DEBUG | |
| `log.info(event, **kw)` | INFO | |
| `log.warning(event, **kw)` | WARNING | |
| `log.error(event, **kw)` | ERROR | |
| `log.critical(event, **kw)` | CRITICAL | |
| `log.exception(event, **kw)` | ERROR | captures current exception automatically — use inside `except` blocks |

`log.exception` is shorthand for `log.error(..., exc_info=True)` — no manual `sys.exc_info()` needed.

!!! tip "Level filtering is zero-cost"
    `make_filtering_bound_logger(logging.INFO)` bakes the minimum level into the class at config time. Calls below the threshold become no-ops — no dict construction, no processor chain traversal.

### Changing the level

- **Native mode** (`wrapper_class=structlog.stdlib.BoundLogger` not set) — level lives in `wrapper_class`; there's no `setLevel()`, re-run `configure()` with a new threshold to change it:

  ```python
  structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.WARNING), ...)
  ```

- **stdlib mode** (`wrapper_class=structlog.stdlib.BoundLogger`) — `make_filtering_bound_logger` doesn't apply; set the level on the stdlib logger as usual: `logging.getLogger().setLevel(logging.DEBUG)`.

To suppress one specific event rather than a whole level tier, raise `structlog.DropEvent` from a processor:

```python
def drop_health_checks(logger, method, event_dict):
    if event_dict.get("event") == "health_check":
        raise structlog.DropEvent()
    return event_dict
```

## Bound logger

`log.bind(**kw)` returns a new logger with those keys permanently attached:

```python
bound = log.bind(service="pricing", symbol="BTC")
bound.info("price_fetched", price=42.0)
# every future call carries service= and symbol=
```

`log.unbind("symbol")` removes a key. `log.new(**kw)` resets all context.

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

Requires `merge_contextvars` as the first processor in the chain.

## Install

```bash
pip install structlog
```

## See also

- [structlog-config.md](structlog-config.md) — the processor pipeline and `structlog.configure()`
- [structlog-testing.md](../tooling/testing/structlog-testing.md) — `capture_logs()`, assertion patterns, pytest fixture, comparison with `caplog`
