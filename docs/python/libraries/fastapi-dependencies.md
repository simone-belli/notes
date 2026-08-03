---
tags:
  - design-patterns
  - testing
  - typing
---

# FastAPI — Dependency Injection, Testing & Auth

`Depends()` is FastAPI's dependency-injection mechanism, and almost everything built on top of the request pipeline flows through it: request-scoped resources, repository wiring, test doubles, and auth guards are all just dependencies. This page covers `Depends()` and its three big applications — injecting collaborators, testing with `TestClient` + overrides, and gating requests with an API-key check. The request/response model itself (routing, params, `response_model`) is in [FastAPI](fastapi.md).

## Dependency Injection — `Depends()`

Path/query/body params all come from the HTTP request directly. Some inputs can't:

- database session (must open per-request, close after)
- current user (derived from auth header + database lookup)
- config / rate limiter

`Depends(f)` is a deferred call token: "call `f` at request time and inject its return value here."

```python
from fastapi import Depends, Request

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

1. **Request-scoped resources** — manual injection wires at startup; `Depends` wires at request time, giving factories access to live request data. You can't pass a database session in `__init__` because it doesn't exist until the request arrives.
2. **Automatic deduplication** — with `use_cache=True` (default), each factory is called at most once per request. If two dependencies both declare `Depends(get_db)`, one session is shared between them; no manual threading required.

!!! note "Decoration time vs request time"
    `get_dependant()` runs at `@app.get(...)` — it inspects signatures and builds the dependency tree.
    `solve_dependencies()` runs per request — it walks the tree, calls factories, caches results.

## Injecting a repository — same as constructor injection

`Depends` is just [constructor injection](../language/objects/repository-di.md) that the framework resolves for you. Write a provider that returns the concrete implementation **typed as the Protocol**, then depend on it:

```python
from typing import Annotated
from fastapi import Depends

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
    `client = TestClient(app)` does **not** fire the app's `lifespan` (startup/shutdown) handlers. If startup opens a database pool or loads a model, wrap it: `with TestClient(app) as client:` runs startup on enter, shutdown on exit. Skip the `with` only when the app has no lifespan events.

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

For a test that must `await` itself, use `httpx.AsyncClient` with an Asynchronous Server Gateway Interface (ASGI) transport — `ASGITransport(app=app)` — instead; `TestClient` (sync) covers nearly all endpoint tests.

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

## Related

- [FastAPI](fastapi.md) — the request/response model these dependencies plug into (routing, params, `response_model`)
- [repository-di.md](../language/objects/repository-di.md) — manual DI with Protocol + `__init__` injection; the pattern `Depends()` extends
- [pydantic/pydantic-settings.md](pydantic/pydantic-settings.md) — where the API key and other config live
- [fixtures.md](../tooling/testing/fixtures.md) — pytest fixtures for wrapping `TestClient` and resetting overrides
