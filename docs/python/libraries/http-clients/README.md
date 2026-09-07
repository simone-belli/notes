# Python — Libraries / HTTP Clients

Libraries for *making* HTTP requests, and the two near-substitutes you choose between — [FastAPI](../fastapi/) and [Uvicorn](../uvicorn.md) are the serving side.

:material-text-box-outline: **[aiohttp](aiohttp.md){ .lvl-intermediate }**
:   Async HTTP client: ClientSession, requests, timeouts, error handling

:material-text-box-outline: **[aiohttp — Concurrency](aiohttp-concurrency.md){ .lvl-advanced }**
:   Many requests at once: gather + semaphore, connector limits, streaming bodies, async retry with backoff

:material-text-box-outline: **[HTTPX](httpx.md){ .lvl-intermediate }**
:   One HTTP client for sync and async: Client vs transport, sending requests, responses, error hierarchy, timeouts, porting from `requests`

:material-text-box-outline: **[HTTPX — Advanced](httpx-advanced.md){ .lvl-advanced }**
:   Async fan-out with gather + semaphore, streaming, retries with backoff, `httpx.Auth` flows, MockTransport/ASGITransport, HTTP/2 and TLS
