# aiohttp

Async HTTP client (and server) library for [asyncio](../language/runtime/asyncio.md). The standard replacement for `requests` in async code — suspends the coroutine during network waits instead of blocking the thread.

---

## ClientSession — the core abstraction

Manages a connection pool, cookie jar, and request defaults. **Create one session per application, not one per request.**

```python
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

---

## Concurrent requests

```python
async def fetch_one(session, url):
    async with session.get(url) as resp:
        resp.raise_for_status()
        return await resp.json()

async def fetch_all(urls):
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
        return await asyncio.gather(
            *[fetch_one(session, url) for url in urls],
            return_exceptions=True,
        )
```

Cap concurrency with a semaphore for rate-limited APIs:
```python
sem = asyncio.Semaphore(5)

async def fetch_one(session, url):
    async with sem:
        async with session.get(url) as resp:
            return await resp.json()
```

---

## Connection pool

```python
aiohttp.ClientSession(
    connector=aiohttp.TCPConnector(limit=100, limit_per_host=10)
)
```

---

## Streaming

For large downloads or streaming APIs (SSE, NDJSON), don't buffer the whole body:

```python
async with session.get(url) as resp:
    async for chunk in resp.content.iter_chunked(65536):
        file.write(chunk)

# line-by-line (SSE / NDJSON)
async for line in resp.content:
    process(line.strip())
```

---

## Gotchas

- `resp.json()` raises if `Content-Type` is not JSON — use `await resp.json(content_type=None)` to skip the check.
- `time.sleep()` and `requests.get()` inside an async function freeze the whole event loop — use `await asyncio.sleep()` and async libraries.
- Always `async with` the session, or call `await session.close()` manually.

---

## See also

- [asyncio.md](../language/runtime/asyncio.md) — event loop, gather, create_task
- [market-data-apis.md](../../tools/market-data-apis.md) — free public endpoints to call with aiohttp
