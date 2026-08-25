# FastAPI — App Structure

What [FastAPI](fastapi.md) is actually made of, how a request travels through
it, and how an app is split across files as it grows past one module.

## Three building blocks

FastAPI coordinates three components:

| Component | Role |
|-----------|------|
| **Starlette** | Asynchronous Server Gateway Interface (ASGI) routing, `Request`/`Response` objects, middleware, WebSockets |
| **Pydantic** | Validation + coercion of incoming params; serialisation of responses; JSON Schema for OpenAPI |
| **`inspect`** | Reads annotations from function signatures at decoration time |

FastAPI itself is mostly the glue: it uses `inspect` to understand what each endpoint needs, Pydantic to enforce it, and Starlette to shuttle bytes in and out.

## Request lifecycle

```
HTTP request
  → Starlette router matches URL → selects APIRoute
  → FastAPI extracts raw values (path / query / headers / body)
  → Pydantic validates + coerces          (type mismatch → 422 auto)
  → solve_dependencies() resolves Depends() tree
  → endpoint function called with typed, validated args
  → return value serialised via response_model
  → HTTP response
```

## At decoration time: `inspect` builds a dependency tree

When `@app.get(...)` runs, FastAPI calls `inspect.signature(fn)` immediately. For each parameter it decides:

- annotation is `int` / `str` + name matches path segment → **path param**
- annotation is `int` / `str` + not in path → **query param**
- annotation is a Pydantic model → **request body**
- default is `Depends(f)` → **dependency** (recurse into `f`'s signature)

The result is a `Dependant` tree stored on the route — built once, reused per request.

!!! tip "Annotation = contract"
    `trade_id: int` is not just a type hint for mypy. FastAPI reads it at runtime to decide where to find the value, how to validate it, and what to put in the OpenAPI spec.

## `APIRouter`: splitting an app into modules

A single `FastAPI()` app in one file doesn't scale. `APIRouter` is a **mini-app** you register routes on exactly like the main app, then attach to the app (or to another router) with `include_router`. It carries no server of its own — it's a collection of routes that gets merged in.

```python
# routers/trades.py
from fastapi import APIRouter

router = APIRouter(prefix="/trades", tags=["trades"])

@router.get("/{trade_id}")          # real path: /trades/{trade_id}
def get_trade(trade_id: int) -> Trade: ...

@router.post("")                    # real path: /trades
def create_trade(trade: Trade) -> Trade: ...
```

```python
# main.py
from fastapi import FastAPI
from routers import trades, users

app = FastAPI()
app.include_router(trades.router)
app.include_router(users.router)
```

- Same decorators as the app (`get`, `post`, `api_route`, …) with identical semantics — a router *is* the sub-app scope those decorators already live on.
- `prefix` is prepended to every path in the router (no trailing slash; `""` matches the bare prefix). `tags` groups the routes in `/docs`.
- `include_router` copies the router's routes into the target at call time — order of inclusion sets the order routes are matched.

**Options set once on the router** apply to all its routes, and `include_router` can add another layer on top:

```python
router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],   # runs for every route (see Depends page)
    responses={404: {"description": "Not found"}},
)

app.include_router(router, prefix="/v1")     # extra prefix → /v1/admin/...
```

- `dependencies=[...]` on a router (or on `include_router`) runs for every route beneath it — the idiomatic place for auth guards that cover a whole section. These use `Depends()` for the side effect only; there's no parameter to receive the value.
- Prefixes and `tags`/`dependencies` **compose**: those on `include_router` stack on top of those on the `APIRouter`.

!!! tip "Router = organisation, not a new runtime"
    An `APIRouter` changes nothing about how requests are handled — the [lifecycle](#request-lifecycle), validation, and `response_model` are identical. It's purely a **source-code** boundary: split routes across files, apply shared prefix/tags/dependencies to a group, and keep `main.py` a thin list of `include_router` calls.

Routers nest — a router can `include_router` another before the app includes it — letting you build `/v1` → `/v1/trades` → `/v1/trades/{id}` hierarchies from small files.

## Dependency injection, testing, and auth

`Depends()` — request-scoped resources, injecting a repository, and an API-key guard — is covered in [Dependency Injection](dependencies.md); swapping a provider for a fake with `dependency_overrides` is in [Testing](testing.md).

## Lifespan: startup and shutdown

Some work happens **once per process**, not per request: open a DB connection pool, create a shared [aiohttp](../aiohttp.md) `ClientSession`, load an ML model, warm a cache — and tear each down cleanly on exit. **Lifespan** is an async context manager passed to `FastAPI(lifespan=...)`; everything before `yield` is startup, everything after is shutdown.

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
import aiohttp

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = aiohttp.ClientSession()   # startup: before any request
    yield                                       # <-- app serves here
    await app.state.http.close()                # shutdown: after requests drain

app = FastAPI(lifespan=lifespan)
```

- The `yield` **is** the running server: setup runs, control blocks at `yield` for the whole serving lifetime, then teardown runs on shutdown.
- Hand resources to handlers by stashing on `app.state` (read via `request.app.state`, ideally behind a `Depends` wrapper for testability), or by **yielding a dict** — its keys land on `request.state`.
- Replaces the deprecated `@app.on_event("startup")` / `@app.on_event("shutdown")` callbacks. One function means teardown sees startup's local variables via closure, and resources that are themselves context managers nest under a single `async with`.

Lifespan is part of the [ASGI](../uvicorn.md) spec and **driven by the server**: [Uvicorn](../uvicorn.md) sends `lifespan.startup` before binding traffic and `lifespan.shutdown` on `SIGTERM`/`SIGINT`.

- **Startup blocks serving** — no request is accepted until setup reaches `yield`, so resources are guaranteed ready. If startup raises, the app never serves.
- **Shutdown is graceful-only** — a `kill -9` or hard crash skips teardown, so don't rely on it for correctness-critical flushing.

!!! warning "Once per worker, not once per app"
    `uvicorn --workers 4` forks four processes; each runs the lifespan independently with its **own** pool, session, model, and [event loop](../../language/concurrency/asyncio.md). Nothing here is shared across workers — an in-process cache is per-worker; cross-worker state needs Redis or similar.

!!! tip "Lifespan vs. `Depends(...)` with `yield` — scope, not syntax"
    Both do setup-before / teardown-after, but lifespan runs **once per process** while a `yield` dependency runs **once per request**. The idiomatic pairing: the connection **pool** lives in the lifespan (created once); a per-request **connection/transaction** is a [`yield` dependency](dependencies.md) that acquires from it and returns it when the response is sent.

!!! warning "`TestClient` only runs lifespan inside `with`"
    `TestClient(app)` alone does **not** fire startup/shutdown — endpoints reading `app.state` set up there hit `AttributeError`. Use it as a context manager: `with TestClient(app) as client:`. (Overriding the resource dependency in tests sidesteps this — the real lifespan never runs.)

## Server vs client — FastAPI is not an HTTP client

FastAPI is a **server**: it answers inbound requests (`caller → you`). An HTTP **client** — [aiohttp](../aiohttp.md), `httpx`, `requests` — does the opposite: it makes outbound requests (`you → some API`). They sit on opposite sides of the HTTP boundary and are **not substitutes**. "Call FastAPI to fetch data" is incoherent: inside a fetch there is no inbound request to serve.

When code both fetches upstream data *and* exposes its own API, keep the two in separate layers:

- **Pure library function** (client side) — fetches with aiohttp, returns a domain object (e.g. a `DataFrame`); knows nothing about being served over HTTP.
- **Thin endpoint** (server side) — a separate module that *calls* that function and converts the result to the wire format at the boundary.

```python
# data/binance.py — pure, framework-free
async def fetch_binance(symbol: str) -> pd.DataFrame: ...

# api/routes.py — FastAPI boundary
@app.get("/klines/{symbol}")
async def get_klines(symbol: str) -> list[Kline]:
    df = await fetch_binance(symbol)   # call the pure core
    return df.to_dict("records")       # convert at the edge
```

The core never imports FastAPI; the boundary holds no fetch logic. This keeps the fetch reusable (CLI, notebook, batch job — none of which run a server) and each layer testable in isolation — the same edges-only-I/O instinct as the [repository pattern](../../language/objects/repository-di.md). A server is often *also* a client (an endpoint may call other services with aiohttp while serving a request); direction is per-connection, not per-process.

## Related

- [FastAPI](fastapi.md) — annotations as contract, path/query/body params, `response_model`
- [Dependency Injection](dependencies.md) — `Depends()`, repository providers, and the API-key guard
- [Testing](testing.md) — `TestClient` and `dependency_overrides`
- [Uvicorn & Ports](../uvicorn.md) — the ASGI server that binds a port and calls the app
- [aiohttp.md](../aiohttp.md) — the HTTP *client* side of the server/client boundary
