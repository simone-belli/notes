---
tags:
  - concurrency
quiz: detail
---

# aiohttp

Async HTTP client (and server) library for [asyncio](../language/concurrency/asyncio.md). The standard replacement for `requests` in async code — suspends the coroutine during network waits instead of blocking the thread. [httpx](httpx.md) is the other common choice; it covers sync and async with one API, while aiohttp is async-only but also ships a server.

---

## ClientSession — the core abstraction

!!! warning "Create one ClientSession per application, not one per request"
    Each `ClientSession()` creates a new TCP connection pool. Creating and destroying a session per request throws away those connections, adding TLS handshake overhead on every call and defeating HTTP keep-alive. Create one session at startup (or in the top-level `async with` block) and share it across all requests.

Manages a connection pool, cookie jar, and request defaults. **Create one session per application, not one per request.**

```python
import aiohttp, asyncio

# BAD — new TCP connection on every call
async def fetch(url):
    async with aiohttp.ClientSession() as session:  # ← don't do this in a loop
        async with session.get(url) as resp:
            return await resp.text()

# GOOD — one session, many requests
async def main(urls):
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(*[fetch(session, url) for url in urls])
```

---

## Basic request

```python
import aiohttp, asyncio

async def main():
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.frankfurter.app/latest") as resp:
            resp.raise_for_status()       # raises ClientResponseError on 4xx/5xx
            data = await resp.json()      # body is read lazily here
    return data

result = asyncio.run(main())
```

**Body reading methods** (all are coroutines — must `await`):

| Method | Returns |
|---|---|
| `await resp.json()` | dict/list |
| `await resp.text()` | str |
| `await resp.read()` | bytes |
| `resp.status` | int (attribute, not coroutine) |

---

## Requests

```python
session.get(url, params={"page": 2})           # query string
session.post(url, json={"key": "val"})          # JSON body
session.post(url, data={"key": "val"})          # form-encoded body
session.put(url, headers={"X-Token": "abc"})    # per-request headers
```

Default session headers / base URL:
```python
aiohttp.ClientSession(
    base_url="https://api.example.com",
    headers={"Authorization": f"Bearer {token}"},
)
# then: session.get("/v1/data")
```

---

## Timeouts

No default — always set one:

```python
timeout = aiohttp.ClientTimeout(total=30, connect=5)
aiohttp.ClientSession(timeout=timeout)
```

Raises `asyncio.TimeoutError` when exceeded.

---

## Error handling

```python
try:
    async with session.get(url) as resp:
        resp.raise_for_status()
        data = await resp.json()
except aiohttp.ClientResponseError as e:    # 4xx/5xx
    print(f"HTTP {e.status}: {e.message}")
except aiohttp.ClientConnectorError:        # DNS/connection failure
    ...
except asyncio.TimeoutError:
    ...
```

Fanning these calls out — `gather` with a semaphore, connector limits, streaming
bodies, and retry with backoff — is covered in
[aiohttp-concurrency.md](aiohttp-concurrency.md).

---

## Gotchas

- `resp.json()` raises if `Content-Type` is not JSON — use `await resp.json(content_type=None)` to skip the check.
- `time.sleep()` and `requests.get()` inside an async function freeze the whole event loop — use `await asyncio.sleep()` and async libraries.
- Always `async with` the session, or call `await session.close()` manually.

---

## See also

- [aiohttp-concurrency.md](aiohttp-concurrency.md) — many requests at once: semaphores, pooling, streaming, retry
- [httpx.md](httpx.md) — the sync-and-async alternative, with a side-by-side comparison
- [asyncio.md](../language/concurrency/asyncio.md) — event loop, gather, create_task
- [market-data-apis.md](../../finance/market-data-apis.md) — free public endpoints to call with aiohttp
- [fastapi.md](fastapi/fastapi.md) — the *server* side of the boundary; a client library and a server framework aren't substitutes
