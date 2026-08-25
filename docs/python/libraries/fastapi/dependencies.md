---
tags:
  - design-patterns
  - typing
---

# FastAPI — Dependency Injection

`Depends()` is FastAPI's dependency-injection mechanism, and almost everything built on top of the request pipeline flows through it: request-scoped resources, repository wiring, test doubles, and auth guards are all just dependencies. This page covers `Depends()` itself, injecting collaborators, and gating requests with an API-key check; swapping a dependency for a fake is in [Testing](testing.md), and the request/response model itself (routing, params, `response_model`) is in [FastAPI](fastapi.md).

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

Two things `Depends()` adds over [manual `__init__` injection](../../language/objects/repository-di.md):

1. **Request-scoped resources** — manual injection wires at startup; `Depends` wires at request time, giving factories access to live request data. You can't pass a database session in `__init__` because it doesn't exist until the request arrives.
2. **Automatic deduplication** — with `use_cache=True` (default), each factory is called at most once per request. If two dependencies both declare `Depends(get_db)`, one session is shared between them; no manual threading required.

!!! note "Decoration time vs request time"
    `get_dependant()` runs at `@app.get(...)` — it inspects signatures and builds the dependency tree.
    `solve_dependencies()` runs per request — it walks the tree, calls factories, caches results.

## Injecting a repository — same as constructor injection

`Depends` is just [constructor injection](../../language/objects/repository-di.md) that the framework resolves for you. Write a provider that returns the concrete implementation **typed as the Protocol**, then depend on it:

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

## API-key check as a dependency (a toy guard)

A dependency that raises `HTTPException` *is* a gate: if it raises, the handler
never runs. That makes a minimal "keep randoms out" check a few lines — read a
secret header, compare it to the configured key, reject on mismatch.

The key lives in [`Settings`](../pydantic/pydantic-settings.md), never hardcoded —
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
- [Testing](testing.md) — `TestClient` and `dependency_overrides`, which swap these providers for fakes
- [repository-di.md](../../language/objects/repository-di.md) — manual DI with Protocol + `__init__` injection; the pattern `Depends()` extends
- [pydantic/pydantic-settings.md](../pydantic/pydantic-settings.md) — where the API key and other config live
