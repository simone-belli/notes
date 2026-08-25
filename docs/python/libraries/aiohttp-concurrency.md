---
tags:
  - concurrency
---

# aiohttp — Concurrency

One request at a time is the easy case. Firing thousands introduces three
separate problems — how many run at once, how many sockets are open, and what
happens when one fails — each with its own knob. All of the below assumes a
single shared session, as in [aiohttp.md](aiohttp.md).

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

The semaphore caps *in-flight coroutines*; the connector caps *open sockets*. Both matter: without a connector limit, a generous semaphore can still exhaust file descriptors or trip a server's per-client connection cap.

---

## Streaming

For large downloads or streaming APIs (Server-Sent Events (SSE), newline-delimited JSON (NDJSON)), don't buffer the whole body:

```python
async with session.get(url) as resp:
    async for chunk in resp.content.iter_chunked(65536):
        file.write(chunk)

# line-by-line (SSE / NDJSON)
async for line in resp.content:
    process(line.strip())
```

See [jsonl.md](jsonl.md) for the on-disk side of the same format.

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

Don't retry [4xx](../../tools/web/http-status-codes.md) — check `e.status >= 500` on `ClientResponseError` first.

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

## See also

- [aiohttp.md](aiohttp.md) — sessions, requests, timeouts, error handling
- [asyncio.md](../language/concurrency/asyncio.md) — `gather`, `create_task`, and the event loop underneath
- [decorators.md](../language/functional/decorators.md) — why the retry wrapper needs three levels of nesting
