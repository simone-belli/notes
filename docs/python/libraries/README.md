# Python — Libraries

Third-party libraries your program imports at runtime — as opposed to [tooling/](../tooling/), the development-time tools you run.

:material-text-box-outline: **[aiohttp](aiohttp.md){ .lvl-intermediate }**
:   Async HTTP client: ClientSession, requests, timeouts, error handling

:material-text-box-outline: **[aiohttp — Concurrency](aiohttp-concurrency.md){ .lvl-advanced }**
:   Many requests at once: gather + semaphore, connector limits, streaming bodies, async retry with backoff

:material-api: **[FastAPI](fastapi/)**

:material-text-box-outline: **[JSON Lines (JSONL)](jsonl.md){ .lvl-basic }**
:   JSON Lines: append-friendly, streamable records with Pydantic serialisation

:material-clipboard-check-outline: **[Pydantic](pydantic/)**

:material-text-box-outline: **[structlog](structlog.md){ .lvl-intermediate }**
:   Structured logging: log methods, context binding, `contextvars` in async code

:material-text-box-outline: **[structlog — Configuration](structlog-config.md){ .lvl-advanced }**
:   The processor pipeline and `structlog.configure()`: native vs stdlib mode, renderer selection, dev vs prod chains

:material-text-box-outline: **[Printing Tables in the Terminal](terminal-tables.md){ .lvl-basic }**
:   Print tables in the terminal: f-strings, tabulate, rich

:material-text-box-outline: **[Uvicorn & Ports](uvicorn.md){ .lvl-intermediate }**
:   The ASGI server that serves a FastAPI app: ports, `--host`/`--port`, import string, one event loop, workers
