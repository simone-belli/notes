---
tags:
  - cli
  - concurrency
---

# Uvicorn & Ports

A `FastAPI()` app is just a callable — it turns a request into a response but has **no way to receive one**. It doesn't open a socket or speak HTTP. An **ASGI server** does that and *calls* your app; the usual choice is **uvicorn**, and the place it listens is a **port**. Uvicorn is the "server" piece [FastAPI](fastapi.md) deliberately leaves out.

## Ports

A host has one IP address but many network programs; the **port** (a number, 0–65535) says *which program* the bytes are for. `(IP, port)` identifies one endpoint; a TCP connection is the 4-tuple `(src IP, src port, dst IP, dst port)`.

- A **server** *binds* a port and listens. Only one process can listen on a given `(host, port)` — a second one gets `Address already in use`.
- A **client** doesn't pick its port; the OS assigns a throwaway high (**ephemeral**) one. The client only cares about the *destination* port.

Ranges:

| Range | Name | Notes |
|-------|------|-------|
| 0–1023 | well-known | needs root on Unix — 22 SSH, 80 HTTP, 443 HTTPS |
| 1024–49151 | registered | app dev, no root — 8000 uvicorn, 5432 PostgreSQL, 6379 Redis |
| 49152–65535 | ephemeral | what the OS hands to clients |

8000 isn't special — just a conventional root-free default. In production a reverse proxy (nginx) owns 80/443 and forwards to the app's high port.

!!! note "Host = which interface (`--host`)"
    Binding needs an interface *and* a port. `127.0.0.1` (`localhost`, **loopback**) = reachable only from the same machine — the safe dev default. `0.0.0.0` = **all** interfaces, reachable from the network — required inside Docker or on a server, but don't do it carelessly on an untrusted network. `0.0.0.0` is a bind wildcard, not an address you connect *to*.

A URL carries the port after a colon (`http://localhost:8000/x`); omit it and the browser uses the scheme default (80 for `http`, 443 for `https`) — which is why public sites need no `:80` but your dev server needs `:8000` spelled out.

## Uvicorn — the ASGI server

Uvicorn binds the socket, parses HTTP off the wire, packages each request as an ASGI event, `await`s your app, and streams the response back — all on a single `asyncio` event loop.

ASGI (Asynchronous Server Gateway Interface) is the contract between an async web *app* and the *server* that drives it; WSGI (Web Server Gateway Interface) was its synchronous predecessor (gunicorn + Flask). FastAPI *is* an ASGI app; uvicorn is an ASGI server. They meet only at the ASGI interface — you can swap in Hypercorn or Daphne without touching the app.

An ASGI app is any callable `async def app(scope, receive, send)`. `FastAPI()` builds exactly that call signature, so `app = FastAPI()` *is* a valid ASGI app — uvicorn just needs pointing at it.

Beyond per-request traffic, uvicorn also drives the ASGI **lifespan** protocol: it sends a startup event before binding the socket to traffic and a shutdown event on `SIGTERM`/`SIGINT`, which is what runs a FastAPI app's [lifespan](fastapi-app-structure.md#lifespan-startup-and-shutdown) setup and teardown. Each `--workers` process runs that lifespan independently.

### Running it

The CLI takes an **import string** `module:attribute` (not a filename — it does `import main; main.app`):

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

- `--host` / `--port` — bind address and port (defaults `127.0.0.1:8000`).
- `--reload` — restart on file change. **Dev only** (runs a file-watcher).
- `--workers N` — fork N processes (see below).

Programmatically — pass the **import string** if you want reload/workers (they re-import in child processes), or the **app object** for a plain single run:

```python
import uvicorn

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    # uvicorn.run(app, ...) also works, but then no reload/workers
```

The `if __name__ == "__main__":` guard matters: reload/workers re-import the module, and without it that re-import would recursively re-trigger `uvicorn.run`.

### One loop, and workers

Uvicorn is **single process, single event loop** by default — thousands of *concurrent* connections but only one CPU core.

!!! warning "Never block the event loop"
    `async def` endpoints share one loop cooperatively. A blocking call (`time.sleep`, heavy CPU, a sync DB driver) **stalls the whole loop** and freezes every other request. Keep the loop non-blocking; offload blocking work to a threadpool or process. See [asyncio](../language/concurrency/asyncio.md).

For multiple cores: `--workers N` forks N independent single-loop processes behind a shared socket (roughly `2 × cores + 1`; no shared memory, so in-process caches are per-worker). The classic production pattern is gunicorn as process manager with uvicorn's worker class: `gunicorn -k uvicorn.workers.UvicornWorker -w 4 main:app`.

### Where it sits

```
client → [ nginx :443, TLS ] → [ uvicorn :8000, HTTP + event loop ] → [ FastAPI app ]
```

Dev usually skips the proxy and hits uvicorn directly on `http://localhost:8000`. Production puts a reverse proxy on 443 (TLS termination) forwarding plaintext to uvicorn on a private high port. A Platform-as-a-Service like [Render](../../tools/web/render.md) supplies that proxy and TLS for you — you just give it the uvicorn start command binding `0.0.0.0:$PORT`.

### Common failures

- `Address already in use` — the port is held (a stale uvicorn). `lsof -i :8000` and kill it, or change `--port`.
- Unreachable from another machine/container host — you bound `127.0.0.1`, not `0.0.0.0`.
- `Error loading ASGI app. Could not import module "main"` — wrong import string or wrong working directory.
- Hangs under load — a blocking call on the loop, or you need workers.

## Related

- [FastAPI](fastapi.md) — the ASGI app uvicorn serves; uvicorn is the server FastAPI leaves out
- [asyncio](../language/concurrency/asyncio.md) — the event loop uvicorn runs; why blocking it freezes every request
- [HTTP Status Codes](../../tools/web/http-status-codes.md) — what the responses uvicorn writes back mean
