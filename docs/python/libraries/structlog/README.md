# Python — Libraries / structlog

Structured logging, where every call emits a dictionary rather than a formatted string: the calling API and context binding, the processor pipeline that turns those dictionaries into JSON or coloured console output, and how to assert on them in tests.

:material-text-box-outline: **[Configuration](config.md){ .lvl-advanced }**
:   The processor pipeline and `structlog.configure()`: native vs stdlib mode, renderer selection, dev vs prod chains

:material-text-box-outline: **[structlog](structlog.md){ .lvl-intermediate }**
:   Structured logging: log methods, context binding, `contextvars` in async code

:material-text-box-outline: **[Testing](testing.md){ .lvl-advanced }**
:   Asserting on structlog output: `capture_logs`, patterns, `caplog` comparison
