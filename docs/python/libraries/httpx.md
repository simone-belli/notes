---
tags:
  - concurrency
  - testing
---

# HTTPX

HTTP client library with **one API for both sync and async** — `requests`'
ergonomics plus `await`, HTTP/2, and a pluggable transport layer. It is the
default client of the modern Python web stack: FastAPI's `TestClient` wraps it,
and most current API software development kits (SDKs) are built on it.

```bash
pip install httpx            # core
pip install 'httpx[http2]'   # + HTTP/2 support
```

---

## Client = policy, transport = mechanism

The one idea that explains the library. A `Client` handles redirects, auth,
cookies, `base_url`, and event hooks, then hands a request to a **transport**,
whose entire interface is one method:

```python
def handle_request(self, request: httpx.Request) -> httpx.Response: ...
```

Below that boundary live sockets, connection pooling, and the HTTP/1.1 and
HTTP/2 protocols (delegated to the `httpcore` package). Swapping the transport
therefore swaps the *network* without disturbing anything else — which is where
[testing](#testing-swap-the-transport) and in-process ASGI dispatch come from.

---

## Client, not top-level functions

```python
import httpx

r = httpx.get("https://api.example.com/items")   # convenience only
```

Each top-level call builds a throwaway `Client`: a new connection pool, a new
Transport Layer Security (TLS) handshake, discarded after one request.

!!! warning "Reuse one Client for anything past a single request"
    A TLS handshake costs 1–2 extra round trips, so per-request clients can
    triple small-request latency. Same rule as `requests.Session` and
    `aiohttp.ClientSession`.

```python
with httpx.Client(
    base_url="https://api.example.com",
    headers={"Authorization": f"Bearer {token}"},
    timeout=httpx.Timeout(10.0, read=30.0),
    follow_redirects=True,
) as client:
    r = client.get("/items", params={"page": 2})
```

The client is a context manager; long-lived services create it at startup and
call `client.close()` / `await client.aclose()` at shutdown (in
[FastAPI](fastapi/app-structure.md), the `lifespan` handler).

---

## Sending a request

```python
client.get(url, params={"q": "python", "tag": ["a", "b"]})  # ?q=python&tag=a&tag=b
client.post(url, json={"a": 1})                    # application/json
client.post(url, data={"a": "1"})                  # form-encoded
client.post(url, content=b"raw bytes")             # raw body
client.post(url, files={"f": ("r.csv", b"a,b\n", "text/csv")})  # multipart
```

!!! warning "`data=` is form fields, not the body"
    In `requests`, `data=b"..."` sent a raw body. In HTTPX raw bodies go to
    **`content=`**; `data=` means form encoding only. The single most common
    porting bug.

`headers` and `cookies` merge with the client defaults; `auth`, `timeout` and
`follow_redirects` replace them.

---

## Response

```python
r.status_code   # int          r.json()     # parsed body
r.text          # str          r.content    # bytes
r.headers       # mapping      r.url        # final URL after redirects
r.elapsed       # timedelta    r.history    # redirect chain
r.is_success    # bool (2xx)   r.http_version  # "HTTP/1.1" | "HTTP/2"
```

Unlike aiohttp, **body accessors are not coroutines** even on the async client —
the body is already in memory unless you used `stream()`:

```python
r = await client.get(url)
data = r.json()                # no await
```

Nothing raises on 4xx/5xx by itself; opt in with `raise_for_status()`, which
returns the response so it chains:

```python
data = client.get(url).raise_for_status().json()
```

---

## Exceptions

```
httpx.HTTPError
├── RequestError          request never completed — no response exists
│   ├── TimeoutException  → ConnectTimeout, ReadTimeout, WriteTimeout, PoolTimeout
│   ├── NetworkError      → ConnectError (DNS / refused), ReadError, WriteError
│   ├── ProtocolError, ProxyError, DecodingError, TooManyRedirects
└── HTTPStatusError       a valid response with a 4xx/5xx status
```

The split matters: `RequestError` carries only `.request`, while
`HTTPStatusError` carries `.response` too, so you can read the error body.

```python
try:
    r = client.get(url)
    r.raise_for_status()
except httpx.HTTPStatusError as e:
    log.error("HTTP %s: %s", e.response.status_code, e.response.text[:200])
except httpx.TimeoutException:
    ...
except httpx.RequestError as e:                 # everything else network-y
    log.error("failed %s: %r", e.request.url, e)
```

Don't retry [4xx](../../tools/web/http-status-codes.md) except `429`.

---

## Timeouts

Unlike `requests`, **every request has a 5-second timeout by default**. Four
phases can be set separately:

```python
httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0)
httpx.Timeout(10.0, read=60.0)   # 10s everywhere, read overridden
httpx.Client(timeout=None)       # disabled — rarely what you want
```

!!! note "`read` is per-chunk, not total"
    `read=30` means "no more than 30 s between chunks", so a slow steady
    download never trips it. For a wall-clock cap on the whole operation, wrap
    the call in `async with asyncio.timeout(60):` (Python 3.11+).

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

HTTP/2 is negotiated during the TLS handshake and falls back to HTTP/1.1
silently. Its win is **multiplexing** — many concurrent requests to one host
share a single connection instead of one socket each, often the largest
throughput gain available when hammering a single endpoint.

Verification uses `certifi`'s certificate bundle, not the operating system
store — the usual cause of failures behind a TLS-inspecting corporate proxy.

---

## Porting from `requests`

| Behaviour | `requests` | HTTPX |
|---|---|---|
| Default timeout | none (hangs forever) | **5 seconds** |
| Follows redirects | yes | **no** — `follow_redirects=True` |
| Raw body | `data=b"..."` | `content=b"..."` |
| Session class | `requests.Session()` | `httpx.Client()` |
| `raise_for_status()` returns | `None` | the response (chainable) |
| Async / HTTP/2 | not supported | `AsyncClient` / `http2=True` |

!!! warning "Redirects are the silent difference"
    A ported script starts returning `301`s where it returned `200`s, and
    nothing raises. Set `follow_redirects=True` on the client to restore the
    `requests` behaviour.

---

## HTTPX vs aiohttp

| | HTTPX | [aiohttp](aiohttp.md) |
|---|---|---|
| Sync API | yes | no |
| Server side | client only | includes a web server |
| HTTP/2 | yes | no |
| Body accessors | `r.json()` | `await resp.json()` |
| Raw async throughput | good | faster at very high volume |
| Testing | `MockTransport` / `ASGITransport` | needs `aioresponses` |

Choose HTTPX for a published library (one codebase serves sync and async users),
for testing an ASGI app, and for porting `requests` code. Choose aiohttp when
you need an async HTTP *server* from the same library, or when raw throughput at
very high request volume is the measured bottleneck.

---

## See also

- [aiohttp.md](aiohttp.md) — the async-only alternative; sessions, timeouts, errors
- [aiohttp-concurrency.md](aiohttp-concurrency.md) — the same fan-out and retry patterns in more depth
- [asyncio.md](../language/concurrency/asyncio.md) — the event loop, `gather`, `create_task`
- [testing.md](fastapi/testing.md) — `TestClient`, the HTTPX client FastAPI ships
- [http-request.md](../../tools/web/http-request.md) — what the request being built actually looks like
- [curl.md](../../tools/web/curl.md) — the same operations from the command line
