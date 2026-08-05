---
tags:
  - concurrency
  - design-patterns
  - typing
quiz: core
---

# FastAPI

FastAPI maps Python functions to HTTP endpoints. Its core idea: **type annotations are the single source of truth** — FastAPI reads them at decoration time and derives parsing, validation, serialisation, and API documentation automatically.

## Importing

The package name is `fastapi` (all lowercase); the application class is `FastAPI` (the `app = FastAPI()` you instantiate):

```python
from fastapi import FastAPI

app = FastAPI()
```

Almost everything is exported from the **top-level `fastapi` package** — a flat import surface, not deep submodule paths. Pull request-declaration helpers, DI, routing, and errors straight from `fastapi`:

```python
from fastapi import (
    FastAPI, APIRouter,          # app + sub-app routers
    Query, Path, Body, Header, Cookie, Form, File,  # parameter sources
    Depends,                     # dependency injection
    HTTPException, status,       # errors + status-code constants
    Request, Response,           # raw ASGI objects (re-exported from Starlette)
)
from fastapi.responses import JSONResponse, StreamingResponse  # response classes: fastapi.responses
from fastapi.testclient import TestClient                      # test client: fastapi.testclient
```

- **Domain models are *not* from `fastapi`** — `BaseModel`, `Field` come from `pydantic`; `fastapi` only imports the request-plumbing helpers.
- Only a few things live in submodules: `fastapi.responses`, `fastapi.testclient`, `fastapi.security`, `fastapi.middleware`.

## The problem it solves

Without FastAPI, every endpoint needs the same boilerplate:

```python
# Flask — manual
@app.route("/trades/<trade_id>")
def get_trade(trade_id):
    try:
        trade_id = int(trade_id)
    except ValueError:
        return jsonify({"error": "trade_id must be int"}), 422
    page = int(request.args.get("page", 1))
    result = service.get_trade(trade_id, page)
    return jsonify(result.to_dict())   # manual serialisation, no docs
```

With FastAPI, the annotations do that work:

```python
@app.get("/trades/{trade_id}")
def get_trade(trade_id: int, page: int = 1) -> TradeResponse:
    return service.get_trade(trade_id, page)
```

Same contract, no boilerplate. FastAPI reads `trade_id: int`, extracts the path segment, coerces it to `int`, returns [`422`](../../tools/http-status-codes.md) if it's not valid, and generates OpenAPI docs — all from the annotation.

## Path operation decorators: `get`, `post`, … vs `route`

Every HTTP request carries a **method** (a verb: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`). The path says *what resource*; the method says *what to do to it*. `GET /trades` and `POST /trades` are two different endpoints sharing a path.

FastAPI gives one decorator **per method**:

```python
@app.get("/items/{id}")     # read one
@app.post("/items")         # create (no id yet)
@app.put("/items/{id}")     # replace wholesale
@app.patch("/items/{id}")   # partial update
@app.delete("/items/{id}")  # remove
```

- Each is a thin wrapper that calls the internal `api_route` with `methods=[...]` pre-filled. `get` and `post` differ **only** in that list.
- All of them run the FastAPI machinery: signature inspection, Pydantic validation, `response_model` serialisation, dependency resolution, and OpenAPI/`/docs` registration.
- The verbs follow HTTP conventions — `GET` is *safe* (no state change) and *idempotent*; `POST` is neither (calling twice creates two). `PUT`/`DELETE` are idempotent. This mirrors Representational State Transfer (REST) directly.

`@app.route(path, methods=[...])` is the **generic Starlette registration** FastAPI inherits — a different, lower-level code path:

| | `@app.get`/`@app.post` (`api_route`) | `@app.route` (Starlette) |
|---|---|---|
| Handler signature | typed params (`id: int`, `item: Item`) | one `Request` arg only |
| Validation → 422 | automatic from annotations | none — parse `request` by hand |
| `response_model` / serialisation | yes | no — build `Response` manually |
| In OpenAPI / `/docs` | yes | **no** |
| `Depends()` resolved | yes | no |

!!! warning "Prefer the verb decorators; `route` is a raw escape hatch"
    `@app.route` bypasses everything FastAPI is for — annotations are ignored, nothing is validated or documented. Use it only for raw ASGI mounts or catch-alls. To answer several methods from one FastAPI-aware function, use `@app.api_route("/ping", methods=["GET", "HEAD"])` (the `api_` engine the verb decorators sit on), **not** `route`. The naming is the tell: `api_` = FastAPI's typed machinery; no prefix = Starlette's raw path.

The same decorators (`get`, `post`, …, `api_route`, `route`) also live on `APIRouter` for splitting an app into modules — identical semantics at sub-app scope.

## Declaring inputs: the four parameter sources

A **path operation** is the pair *(method, path)* bound to a function (`@app.get`, `@app.post`, …). The function signature *is* the request schema — FastAPI decides each parameter's source from its annotation:

```python
@app.get("/trades/{trade_id}")
def get_trade(trade_id: int) -> Trade: ...          # path param

@app.get("/trades")
def list_trades(
    status: str = "OPEN",                            # query param (has default → optional)
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,  # query + validation
) -> list[Trade]: ...

@app.post("/trades")
def create_trade(trade: Trade) -> Trade:             # Pydantic model → JSON body
    return repo.save(trade)
```

| Parameter looks like… | Source |
|-----------------------|--------|
| name matches a `{...}` path segment | **path param** |
| scalar (`int`/`str`/…), not in path | **query param** — required if no default |
| a Pydantic model / dataclass | **request body** (JSON) |
| **anything else non-scalar** (`list[...]`, `dict[...]`, `set[...]`) | **request body** (JSON) |
| default is `Depends(...)` | **dependency** |

The rule is really *"scalar ⇒ query, everything else ⇒ body"* — **only scalars auto-map to the query string.** Any type mismatch or constraint violation (`ge`/`le` via `Query`) yields an automatic **422** with field-level detail from Pydantic. You never pull values off a `request` object.

!!! warning "A bare `list[str]` becomes a body, not a repeated query key"
    `def f(symbols: list[str])` is treated as a **request body**, so `GET /x?symbols=A&symbols=B` never populates it and fails validation with **422** — before the function runs. Non-scalar ⇒ body is the default; you opt back out explicitly. To read a repeated query key into a list, annotate with `Query()`:

    ```python
    from typing import Annotated
    from fastapi import Query

    def f(symbols: Annotated[list[str], Query()] = []): ...
    # ?symbols=A&symbols=B  →  ["A", "B"]
    ```

    The mirror trap on `POST`: a lone **scalar** you want in the JSON body is read from the query instead — force it with `Body()` (`x: Annotated[int, Body()]`). Both escape hatches exist because the type alone is ambiguous once you leave the happy path.

## `response_model`: serialise and filter output

The return annotation (or explicit `response_model=`) declares the response shape. It doesn't just format — it **filters**:

```python
@app.get("/trades/{trade_id}")
def get_trade(trade_id: int) -> Trade:
    return repo.get(trade_id)   # Object-Relational Mapping (ORM) row / dict / Trade → serialised to Trade's fields
```

- **Serialises** whatever you return (ORM object, dict, model) into JSON via the model.
- **Filters** to only the model's fields — a `secret` column not on `Trade` is dropped (a security boundary).
- **Validates your own output**, catching contract drift server-side.

!!! tip "Reuse `Trade`, don't redefine it"
    One Pydantic model can be the request body *and* the response model *and* the OpenAPI schema at once — Pydantic does input validation and output serialisation in both directions. Split into separate models (`TradeCreate` without `id`, `Trade` with) only when the shapes genuinely differ, not reflexively.

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

`Depends()` — request-scoped resources, injecting a repository, testing with `TestClient` + `dependency_overrides`, and an API-key guard — is covered on its own page: [FastAPI — Dependency Injection, Testing & Auth](fastapi-dependencies.md).

## Lifespan: startup and shutdown

Some work happens **once per process**, not per request: open a DB connection pool, create a shared [aiohttp](aiohttp.md) `ClientSession`, load an ML model, warm a cache — and tear each down cleanly on exit. **Lifespan** is an async context manager passed to `FastAPI(lifespan=...)`; everything before `yield` is startup, everything after is shutdown.

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

Lifespan is part of the [ASGI](uvicorn.md) spec and **driven by the server**: [Uvicorn](uvicorn.md) sends `lifespan.startup` before binding traffic and `lifespan.shutdown` on `SIGTERM`/`SIGINT`.

- **Startup blocks serving** — no request is accepted until setup reaches `yield`, so resources are guaranteed ready. If startup raises, the app never serves.
- **Shutdown is graceful-only** — a `kill -9` or hard crash skips teardown, so don't rely on it for correctness-critical flushing.

!!! warning "Once per worker, not once per app"
    `uvicorn --workers 4` forks four processes; each runs the lifespan independently with its **own** pool, session, model, and [event loop](../language/concurrency/asyncio.md). Nothing here is shared across workers — an in-process cache is per-worker; cross-worker state needs Redis or similar.

!!! tip "Lifespan vs. `Depends(...)` with `yield` — scope, not syntax"
    Both do setup-before / teardown-after, but lifespan runs **once per process** while a `yield` dependency runs **once per request**. The idiomatic pairing: the connection **pool** lives in the lifespan (created once); a per-request **connection/transaction** is a [`yield` dependency](fastapi-dependencies.md) that acquires from it and returns it when the response is sent.

!!! warning "`TestClient` only runs lifespan inside `with`"
    `TestClient(app)` alone does **not** fire startup/shutdown — endpoints reading `app.state` set up there hit `AttributeError`. Use it as a context manager: `with TestClient(app) as client:`. (Overriding the resource dependency in tests sidesteps this — the real lifespan never runs.)

## Server vs client — FastAPI is not an HTTP client

FastAPI is a **server**: it answers inbound requests (`caller → you`). An HTTP **client** — [aiohttp](aiohttp.md), `httpx`, `requests` — does the opposite: it makes outbound requests (`you → some API`). They sit on opposite sides of the HTTP boundary and are **not substitutes**. "Call FastAPI to fetch data" is incoherent: inside a fetch there is no inbound request to serve.

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

The core never imports FastAPI; the boundary holds no fetch logic. This keeps the fetch reusable (CLI, notebook, batch job — none of which run a server) and each layer testable in isolation — the same edges-only-I/O instinct as the [repository pattern](../language/objects/repository-di.md). A server is often *also* a client (an endpoint may call other services with aiohttp while serving a request); direction is per-connection, not per-process.

## What FastAPI doesn't include

No ORM, no migrations, no admin UI, no project layout opinion — and **no server**: a `FastAPI()` app is an ASGI callable that can't receive a request on its own. An ASGI server like [Uvicorn](uvicorn.md) binds the port and calls it. It does one thing: Python functions ↔ HTTP API, with the glue (validation, serialisation, DI, docs) handled from annotations.

## Related

- [FastAPI — Dependency Injection, Testing & Auth](fastapi-dependencies.md) — `Depends()`, `TestClient`, and the API-key guard
- [pydantic/pydantic.md](pydantic/pydantic.md) — Pydantic is FastAPI's validation and serialisation engine
- [Uvicorn & Ports](uvicorn.md) — the ASGI server that binds a port and actually serves the app
- [asyncio.md](../language/concurrency/asyncio.md) — FastAPI is ASGI-native; endpoint functions can be `async def`
- [aiohttp.md](aiohttp.md) — the HTTP *client* side of the boundary; keep outbound fetches in a pure function and the endpoint thin
