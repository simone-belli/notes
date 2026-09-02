---
tags:
  - errors
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
[testing and in-process Asynchronous Server Gateway Interface (ASGI)
dispatch](httpx-advanced.md#testing-swap-the-transport) come from.

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

## Diagnosing "`.text` looks fine, `.json()` fails"

Check the **content type before the body** — the header alone identifies three
of the four usual causes:

```python
r = httpx.get(url, params=params)
r.raise_for_status()
print(r.status_code, r.headers.get("content-type"))
print(r.text[:300])
```

| Content type | Cause | Fix |
|---|---|---|
| `text/csv`, `text/xml`, … | The API has a format switch you didn't set | Send the format parameter or `Accept` header |
| `text/html` | An error, login, or rate-limit page returned with `200` | Read the page; usually auth or throttling |
| any, empty body | `.json()` on `""` raises the same error | Guard on `if not r.content` |
| `application/json` | A `200` carrying an API-level error envelope | Inspect the parsed body |

Only the last case needs the body read: a wrong content type, an HTML page, and
an empty response are all visible from `r.headers` and `len(r.content)`.

!!! warning "`raise_for_status()` passing means nothing about the format"
    Status and content type are independent. An HTML rate-limit page or a JSON
    error envelope can both arrive as a clean `200`, so a passing
    `raise_for_status()` is not evidence that `.json()` will work — or that the
    parsed result is a success payload.

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

Don't retry [4xx](../../tools/web/http-status-codes.md) except `429` — see
[retries with backoff](httpx-advanced.md#retries) for the `429`/5xx case.

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

- [httpx-advanced.md](httpx-advanced.md) — async fan-out, streaming, retries, auth flows, transport-swap testing, HTTP/2
- [aiohttp.md](aiohttp.md) — the async-only alternative; sessions, timeouts, errors
- [asyncio.md](../language/concurrency/asyncio.md) — the event loop, `gather`, `create_task`
- [testing.md](fastapi/testing.md) — `TestClient`, the HTTPX client FastAPI ships
- [http-request.md](../../tools/web/http-request.md) — what the request being built actually looks like
- [curl.md](../../tools/web/curl.md) — the same operations from the command line
