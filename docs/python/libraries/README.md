# Python — Libraries

Third-party libraries your program imports at runtime — as opposed to [tooling/](../tooling/), the development-time tools you run.

:material-text-box-outline: **[aiohttp](aiohttp.md)**
:   Async HTTP client: ClientSession, concurrency, streaming, error handling

:material-text-box-outline: **[FastAPI — App Structure](fastapi-app-structure.md)**
:   Starlette/Pydantic/`inspect` building blocks, request lifecycle, APIRouter, lifespan, server-vs-client boundary

:material-text-box-outline: **[FastAPI — Dependency Injection, Testing & Auth](fastapi-dependencies.md)**
:   Depends() injection, repository wiring, TestClient + dependency_overrides, API-key guard

:material-text-box-outline: **[FastAPI](fastapi.md)**
:   FastAPI: annotations as contract, path/query/body params, response_model

:material-text-box-outline: **[JSON Lines (JSONL)](jsonl.md)**
:   JSON Lines: append-friendly, streamable records with Pydantic serialisation

:material-folder-outline: **[Pydantic](pydantic/)**
:   Data validation, settings, and validators

:material-text-box-outline: **[structlog](structlog.md)**
:   Structured logging: processor pipeline, context binding, JSON output

:material-text-box-outline: **[Printing Tables in the Terminal](terminal-tables.md)**
:   Print tables in the terminal: f-strings, tabulate, rich

:material-text-box-outline: **[Uvicorn & Ports](uvicorn.md)**
:   The ASGI server that serves a FastAPI app: ports, `--host`/`--port`, import string, one event loop, workers
