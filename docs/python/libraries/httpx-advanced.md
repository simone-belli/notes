---
tags:
  - concurrency
  - testing
---

# HTTPX — Advanced

The parts of [HTTPX](httpx.md) you reach for when hardening a client rather than
writing one: fanning out concurrently, streaming bodies that don't fit in memory,
retrying, authenticating against a challenge/response scheme, and swapping the
transport in tests.

---

## Async and concurrency

`AsyncClient` is the same API with `await`, `async with`, and `aiter_*` in place
of `iter_*`; the `Response` class is literally shared. Fan out with
[`asyncio.gather`](../language/concurrency/asyncio.md) over one client, capped
by a semaphore:

```python
async def fetch_all(urls, concurrency=10):
    sem = asyncio.Semaphore(concurrency)          # created once, shared

    async with httpx.AsyncClient(timeout=10.0) as client:
        async def one(url):
            async with sem:
                r = await client.get(url)
                return r.raise_for_status().json()

        return await asyncio.gather(*(one(u) for u in urls),
                                    return_exceptions=True)
```

The semaphore caps *in-flight coroutines*; `Limits` caps *open sockets*:

```python
httpx.Limits(max_connections=100, max_keepalive_connections=20,
             keepalive_expiry=5.0)
```

Exceeding `max_connections` makes requests queue, and queuing past the `pool`
timeout raises `PoolTimeout` — the signature of "concurrency exceeds pool size".

!!! warning "An AsyncClient binds to one event loop"
    Don't build one at module import and use it across several `asyncio.run()`
    calls — create it inside the loop that will use it.

---

## Streaming

`stream()` yields headers before the body arrives, so large downloads and
open-ended feeds never buffer in memory:

```python
with client.stream("GET", url) as r:
    r.raise_for_status()
    for chunk in r.iter_bytes(chunk_size=65536):   # or iter_lines(), iter_text()
        f.write(chunk)
```

Inside the block `r.text` raises `ResponseNotRead` — iterate, or call `r.read()`
first. Request bodies stream too: pass a generator to `content=`.

---

## Retries

`HTTPTransport(retries=3)` retries only failures to *establish* a connection —
Domain Name System (DNS) errors, connection refused. It never retries a 500, a
429, or a read timeout, since the request was already delivered. For
status-based backoff, use `tenacity`:

```python
@retry(retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
       wait=wait_exponential(multiplier=0.5, max=20),
       stop=stop_after_attempt(4), reraise=True)
async def fetch(client, url):
    r = await client.get(url)
    if r.status_code in {429, 500, 502, 503, 504}:
        r.raise_for_status()
    return r
```

---

## Authentication

```python
httpx.Client(auth=("user", "pass"))                  # Basic
httpx.Client(auth=httpx.DigestAuth("user", "pass"))
httpx.Client(headers={"Authorization": f"Bearer {token}"})
```

Stateful schemes subclass `httpx.Auth`, whose `auth_flow` is a **generator**:
`yield` a request, receive its response, optionally yield another. That maps
directly onto challenge/response flows like token refresh.

```python
class BearerRefreshAuth(httpx.Auth):
    def auth_flow(self, request):
        request.headers["Authorization"] = f"Bearer {self.token}"
        response = yield request
        if response.status_code == 401:
            self.token = self.refresh()
            request.headers["Authorization"] = f"Bearer {self.token}"
            yield request
```

---

## Testing: swap the transport

`MockTransport` answers requests with a plain function — no monkeypatching, and
the client layer above (base URL, auth, redirects, hooks) still runs for real:

```python
def handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"id": 1}) if request.url.path == "/items/1" \
        else httpx.Response(404)

client = httpx.Client(transport=httpx.MockTransport(handler))
```

`respx` layers route matching on top of the same mechanism. `ASGITransport`
instead dispatches into an in-process Asynchronous Server Gateway Interface
(ASGI) app — no socket, no port, real routing and validation:

```python
transport = httpx.ASGITransport(app=app)
async with httpx.AsyncClient(transport=transport,
                             base_url="http://testserver") as client:
    r = await client.get("/items")
```

This is what [FastAPI's `TestClient`](fastapi/testing.md) wraps behind a sync
facade; reach for `AsyncClient` directly only when the test body must `await`.

!!! warning "`AsyncClient(app=app)` was removed in 0.28"
    The shorthand was deprecated in 0.27 and deleted in 0.28 — write
    `transport=httpx.ASGITransport(app=app)`. HTTPX is still pre-1.0 (0.28.1 at
    time of writing) and breaks API in minor releases, so pin it.

---

## HTTP/2, proxies, TLS

```python
httpx.Client(http2=True)                        # needs httpx[http2]
httpx.Client(proxy="http://localhost:8030")     # or mounts={} for per-host
httpx.Client(verify="/path/to/ca.pem")          # custom certificate authority
httpx.Client(cert=("client.pem", "client.key")) # mutual TLS
```

HTTP/2 is negotiated during the Transport Layer Security (TLS) handshake and
falls back to HTTP/1.1 silently. Its win is **multiplexing** — many concurrent
requests to one host share a single connection instead of one socket each, often
the largest throughput gain available when hammering a single endpoint.

Verification uses `certifi`'s certificate bundle, not the operating system
store — the usual cause of failures behind a TLS-inspecting corporate proxy.

---

## See also

- [httpx.md](httpx.md) — the client, requests, responses, exceptions, timeouts
- [aiohttp-concurrency.md](aiohttp-concurrency.md) — the same fan-out and retry patterns in aiohttp
- [asyncio.md](../language/concurrency/asyncio.md) — the event loop, `gather`, `create_task`
- [testing.md](fastapi/testing.md) — `TestClient`, the HTTPX client FastAPI ships
- [mocking-network.md](../tooling/testing/mocking-network.md) — mocking HTTP at each layer
