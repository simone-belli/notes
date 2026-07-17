---
tags:
  - testing
  - logging
quiz: detail
---

# Testing structlog Logs

How to assert on log output from [structlog](../../libraries/structlog.md) in tests.

!!! tip "capture_logs() makes log assertions trivially easy — no patching needed"
    `capture_logs()` is a context manager that temporarily replaces the processor chain and collects events as plain dicts. You can assert on event names, log levels, and structured fields directly. Compare this to stdlib `logging` tests, which require `logging.handlers.MemoryHandler` or `caplog` fixtures and string parsing.

`capture_logs()` temporarily swaps the entire processor chain with one that appends each event dict to a list — no rendering, no I/O. Every keyword arg you passed to the log call survives intact.

```python
from structlog.testing import capture_logs

def test_logs_error_on_failure():
    with capture_logs() as cap:
        process_order(order_id=1)

    assert cap[0]["event"] == "processing_failed"
    assert cap[0]["log_level"] == "error"   # method name, lowercased
    assert cap[0]["order_id"] == 1          # structured field — no string parsing
```

Each captured dict contains `"event"`, `"log_level"`, and every keyword argument passed to the log call. Processor-added fields (timestamp, logger name) are absent — the chain is bypassed.

## Patterns

**Sequence of events:**

```python
events = [e["event"] for e in cap]
assert events == ["step_started", "step_completed"]
```

**Nothing logged (happy path):**

```python
assert cap == []
```

**Bound context is captured:**

```python
bound = log.bind(request_id="abc")
with capture_logs() as cap:
    bound.info("received")
assert cap[0]["request_id"] == "abc"
```

**Exceptions** — `log.exception(...)` stores `exc_info` as a raw `(type, value, traceback)` tuple (no renderer runs):

```python
with capture_logs() as cap:
    try:
        1 / 0
    except ZeroDivisionError:
        log.exception("division_error")

assert cap[0]["exc_info"][0] is ZeroDivisionError
# or just: assert "exc_info" in cap[0]
```

## Pytest fixture

```python
# conftest.py
import pytest
from structlog.testing import capture_logs

@pytest.fixture
def cap_logs():
    with capture_logs() as logs:
        yield logs
```

## Limitations

- Does **not** capture stdlib `logging` calls (third-party libs). Use pytest's `caplog` for those.
- `bind_contextvars` keys are invisible inside `capture_logs()` because `merge_contextvars` is not in the replaced chain. Use `log.bind(...)` in tests instead.

## `capture_logs()` vs `caplog`

| | `capture_logs()` | pytest `caplog` |
|---|---|---|
| Output | List of dicts — fields intact | List of `LogRecord` — needs string parsing |
| Works with | structlog | stdlib `logging` (+ structlog in stdlib mode) |
| Assert on fields | `cap[0]["order_id"] == 1` | parse `.getMessage()` |
| Assert on level | `cap[0]["log_level"] == "error"` | `record.levelname == "ERROR"` |

## Related notes

- [`structlog.md`](../../libraries/structlog.md) — configuration, processor pipeline, bound loggers
- [`pytest.md`](pytest.md) — command quick-reference
