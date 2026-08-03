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

Same contract, no boilerplate. FastAPI reads `trade_id: int`, extracts the path segment, coerces it to `int`, returns `422` if it's not valid, and generates OpenAPI docs — all from the annotation.

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
| default is `Depends(...)` | **dependency** |

Any type mismatch or constraint violation (`ge`/`le` via `Query`) yields an automatic **422** with field-level detail from Pydantic. You never pull values off a `request` object.

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

## Dependency Injection — `Depends()`

Path/query/body params all come from the HTTP request directly. Some inputs can't:

- database session (must open per-request, close after)
- current user (derived from auth header + DB lookup)
- config / rate limiter

`Depends(f)` is a deferred call token: "call `f` at request time and inject its return value here."

```python
def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session           # session closed after response via AsyncExitStack

def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    token = request.headers["Authorization"]
    return db.query(User).filter(...).first()

@app.get("/me")
def me(user: User = Depends(get_current_user)):
    return user
```

Two things `Depends()` adds over [manual `__init__` injection](../language/objects/repository-di.md):

1. **Request-scoped resources** — manual injection wires at startup; `Depends` wires at request time, giving factories access to live request data. You can't pass a DB session in `__init__` because it doesn't exist until the request arrives.
2. **Automatic deduplication** — with `use_cache=True` (default), each factory is called at most once per request. If two dependencies both declare `Depends(get_db)`, one session is shared between them; no manual threading required.

!!! note "Decoration time vs request time"
    `get_dependant()` runs at `@app.get(...)` — it inspects signatures and builds the dependency tree.
    `solve_dependencies()` runs per request — it walks the tree, calls factories, caches results.

## Injecting a repository — same as constructor injection

`Depends` is just [constructor injection](../language/objects/repository-di.md) that the framework resolves for you. Write a provider that returns the concrete implementation **typed as the Protocol**, then depend on it:

```python
def get_trade_repo() -> TradeRepository:        # return type = the interface
    return SqlTradeRepository(get_connection())  # concrete impl built here

@app.get("/trades/{trade_id}")
def get_trade(
    trade_id: int,
    repo: Annotated[TradeRepository, Depends(get_trade_repo)],
) -> Trade:
    return repo.get(trade_id)                    # repo is just a TradeRepository
```

The endpoint sees only `TradeRepository`; `get_trade_repo` is the single wiring point where the concrete class is named — exactly like a `build_service()` factory. Passing it by hand into a constructor would be identical; the framework just resolves the graph per request.

## Testing with `TestClient`

`TestClient` runs the whole app **in-process** — no server, no socket — while executing the *real* pipeline: routing, validation, dependency resolution, `response_model` serialisation, exception handlers. Only the transport is faked.

```python
from fastapi.testclient import TestClient

client = TestClient(app)

def test_read_root():
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json() == {"message": "hello"}
```

- **Wraps `httpx`** — the response is an `httpx.Response` (`.status_code`, `.json()`, `.text`, `.headers`); `httpx` must be installed.
- **Synchronous even for `async def` endpoints** — it runs an event loop internally, so test functions stay plain `def` (no `await`, no `asyncio` marker).

Each parameter source maps to a client argument:

| Endpoint expects | Pass |
|------------------|------|
| path param | in the URL — `client.get(f"/trades/{id}")` |
| query params | `params={"status": "OPEN", "limit": 10}` |
| JSON body (Pydantic model) | `json={"symbol": "BTC"}` |
| form fields (`Form(...)`) | `data={"username": "u"}` |
| file upload (`File(...)`) | `files={"f": ("n.csv", b"...", "text/csv")}` |
| header / cookie | `headers={...}` / `cookies={...}` |

!!! warning "`json=` vs `data=` — the most common mistake"
    `json=` sends a JSON body (for model endpoints); `data=` sends form-encoded fields (for `Form(...)`). Cross them and you get a `422`.

!!! warning "TestClient does not raise on 4xx/5xx"
    A `404` or `500` is a normal return value — assert on `resp.status_code`, there's no exception to catch. Testing the error path is just `assert client.get("/missing").status_code == 404`.

!!! note "Use the context manager to run startup/shutdown"
    `client = TestClient(app)` does **not** fire the app's `lifespan` (startup/shutdown) handlers. If startup opens a DB pool or loads a model, wrap it: `with TestClient(app) as client:` runs startup on enter, shutdown on exit. Skip the `with` only when the app has no lifespan events.

### Override the dependency, touch no DB

`app.dependency_overrides` maps a provider to a replacement. Point `get_trade_repo` at an in-memory fake and the whole app runs against it — no database, real routing/validation/serialisation:

```python
def test_get_trade():
    fake = InMemoryTradeRepository()
    fake.save(Trade(id=42, symbol="BTC", status="OPEN"))
    app.dependency_overrides[get_trade_repo] = lambda: fake

    resp = TestClient(app).get("/trades/42")

    assert resp.json()["symbol"] == "BTC"
    app.dependency_overrides.clear()   # dict lives on app — clear or it leaks
```

Both implementations satisfy the same `TradeRepository` Protocol, so nothing else changes. Prefer a [fake over a mock](../language/objects/repository-di.md) — it exercises the endpoint against correct behaviour. `dependency_overrides` is a plain dict on the `app`, so wrap client + reset in a [pytest fixture](../tooling/testing/fixtures.md) to keep tests isolated:

```python
@pytest.fixture
def client():
    with TestClient(app) as c:        # lifespan runs
        yield c
    app.dependency_overrides.clear()  # teardown resets overrides
```

For a test that must `await` itself, use `httpx.AsyncClient` with `ASGITransport(app=app)` instead; `TestClient` (sync) covers nearly all endpoint tests.

## API-key check as a dependency (a toy guard)

A dependency that raises `HTTPException` *is* a gate: if it raises, the handler
never runs. That makes a minimal "keep randoms out" check a few lines — read a
secret header, compare it to the configured key, reject on mismatch.

The key lives in [`Settings`](pydantic/pydantic-settings.md), never hardcoded —
so it can differ per deployment and rotate without a code change:

```python
# config.py
from pydantic import SecretStr
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    api_key: SecretStr          # required; SecretStr keeps it out of logs/repr
```

```python
import secrets
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from .config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def require_api_key(key: str | None = Depends(api_key_header)) -> None:
    if key is None:                                    # header absent
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing API key")
    if not secrets.compare_digest(key, settings.api_key.get_secret_value()):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid API key")
```

- **`auto_error=False`** — the default (`True`) auto-raises `403` on a missing
  header before your code runs, costing you the 401/403 split. `False` injects
  `None` instead so *you* choose the status.
- **`401` vs `403`** — `401 Unauthorized` means *unauthenticated* ("send
  credentials"): use it when the header is **absent**. `403 Forbidden` means
  *authenticated but not allowed*: use it when a key was sent but is **wrong**.
- **`secrets.compare_digest`, not `==`** — `==` short-circuits on the first
  differing byte, leaking key length/prefix via response timing (a *timing
  attack*). `compare_digest` is constant-time.

Apply it with `dependencies=[...]` (return value ignored — it runs only to
raise-or-pass), at endpoint, router, or app scope:

```python
@app.get("/trades", dependencies=[Depends(require_api_key)])   # one endpoint
router = APIRouter(dependencies=[Depends(require_api_key)])     # whole router
app = FastAPI(dependencies=[Depends(require_api_key)])          # whole app
```

!!! warning "This is a toy guard, not production authentication"
    It's a single shared static secret, which is fine for an internal service or
    demo but is missing everything real auth needs:

    - **No rotation** — one key forever; changing it means editing `.env` and
      redeploying, with no overlapping-validity window and no expiry. A leak
      forces every client to update at once.
    - **No scoping or identity** — all-or-nothing access; you can't grant one
      caller read-only, attribute a request to *who* sent it, or revoke one
      client without breaking all of them (they share the key).
    - **No hashing / per-key management / rate limiting.**

    Real options: OAuth2 / OpenID Connect with short-lived JSON Web Tokens
    (JWTs, via `OAuth2PasswordBearer`), a hashed-key store with per-key scopes +
    expiry + revocation, or auth pushed into an API gateway / mutual TLS. The
    dependency *shape* is unchanged — only what it validates gets richer.

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

No ORM, no migrations, no admin UI, no project layout opinion. It does one thing: Python functions ↔ HTTP API, with the glue (validation, serialisation, DI, docs) handled from annotations.

## Related

- [repository-di.md](../language/objects/repository-di.md) — manual DI with Protocol + `__init__` injection; the pattern `Depends()` extends
- [pydantic/pydantic.md](pydantic/pydantic.md) — Pydantic is FastAPI's validation and serialisation engine
- [asyncio.md](../language/concurrency/asyncio.md) — FastAPI is ASGI-native; endpoint functions can be `async def`
- [aiohttp.md](aiohttp.md) — the HTTP *client* side of the boundary; keep outbound fetches in a pure function and the endpoint thin
