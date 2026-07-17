---
tags:
  - concurrency
quiz: detail
---

# aiohttp

Async HTTP client (and server) library for [asyncio](../language/concurrency/asyncio.md). The standard replacement for `requests` in async code — suspends the coroutine during network waits instead of blocking the thread.

---

## ClientSession — the core abstraction

!!! warning "Create one ClientSession per application, not one per request"
    Each `ClientSession()` creates a new TCP connection pool. Creating and destroying a session per request throws away those connections, adding TLS handshake overhead on every call and defeating HTTP keep-alive. Create one session at startup (or in the top-level `async with` block) and share it across all requests.

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

Cap concurrency with a semaphore for rate-limited APIs. `asyncio.gather()` fires all tasks immediately — 200 URLs means 200 simultaneous requests, which most APIs rate-limit or ban.

!!! warning "Create the Semaphore once outside the coroutine, not inside it"
    Creating `asyncio.Semaphore(10)` inside `fetch_one` gives every coroutine its own private counter — they don't share it and no cap is enforced. Create it once in the outer scope and let the inner function close over it.

```python
async def fetch_all(session, urls, concurrency=10):
    sem = asyncio.Semaphore(concurrency)  # created once, shared by all

    async def fetch_one(url):
        async with sem:                   # blocks when concurrency limit is reached
            async with session.get(url) as resp:
                resp.raise_for_status()
                return await resp.json()

    return await asyncio.gather(*[fetch_one(url) for url in urls], return_exceptions=True)
```

Unlike chunking the list into batches, a semaphore starts the next request the moment any running one finishes — no idle waiting for the slowest item in a batch.

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

## Retry

!!! warning "Sync retry decorators silently fail on async functions"
    A sync wrapper calls `func(*args, **kwargs)`, which returns a coroutine object — not a result. The try/except never sees a network error; the coroutine is discarded unrun. The async wrapper must be `async def` and must `await` the call.

```python
def async_retry(max_attempts=3, base_delay=1.0):
    def decorator(func):
        async def wrapper(*args, **kwargs):          # must be async
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)   # must await
                except aiohttp.ClientResponseError as e:
                    if e.status < 500 or attempt == max_attempts - 1:
                        raise
                    await asyncio.sleep(base_delay * 2**attempt)
                except (aiohttp.ClientError, asyncio.TimeoutError):
                    if attempt == max_attempts - 1:
                        raise
                    await asyncio.sleep(base_delay * 2**attempt)
        return wrapper
    return decorator
```

**Exceptions to catch:**

| Exception | Cause |
|---|---|
| `aiohttp.ClientError` | Base class: DNS, connection refused, bad response |
| `asyncio.TimeoutError` | Timeout exceeded |

Don't retry 4xx — check `e.status >= 500` on `ClientResponseError` first.

**Timeout inside the retried function** — use `asyncio.timeout(n)` (Python 3.11+) to cover the whole block, or `asyncio.wait_for(coro, timeout=n)` for older versions:

```python
@async_retry(max_attempts=3)
async def fetch(session, url):
    async with asyncio.timeout(10):      # Python 3.11+
        async with session.get(url) as resp:
            resp.raise_for_status()
            return await resp.json()
```

For a batteries-included version, `tenacity.AsyncRetrying` supports the same pattern without hand-rolling the loop.

---

## Gotchas

- `resp.json()` raises if `Content-Type` is not JSON — use `await resp.json(content_type=None)` to skip the check.
- `time.sleep()` and `requests.get()` inside an async function freeze the whole event loop — use `await asyncio.sleep()` and async libraries.
- Always `async with` the session, or call `await session.close()` manually.

---

## See also

- [asyncio.md](../language/concurrency/asyncio.md) — event loop, gather, create_task
- [market-data-apis.md](../../finance/market-data-apis.md) — free public endpoints to call with aiohttp
