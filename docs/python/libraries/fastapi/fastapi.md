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

Same contract, no boilerplate. FastAPI reads `trade_id: int`, extracts the path segment, coerces it to `int`, returns [`422`](../../../tools/web/http-status-codes.md) if it's not valid, and generates OpenAPI docs — all from the annotation.

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
## How an app is put together

The components underneath (Starlette, Pydantic, `inspect`), the request
lifecycle, splitting routes across files with `APIRouter`, lifespan startup
and shutdown, and the server-vs-client boundary are covered on their own
page: [FastAPI — App Structure](app-structure.md).

## What FastAPI doesn't include

No ORM, no migrations, no admin UI, no project layout opinion — and **no server**: a `FastAPI()` app is an ASGI callable that can't receive a request on its own. An ASGI server like [Uvicorn](../uvicorn.md) binds the port and calls it. It does one thing: Python functions ↔ HTTP API, with the glue (validation, serialisation, DI, docs) handled from annotations.


## Related

- [FastAPI — App Structure](app-structure.md) — building blocks, request lifecycle, `APIRouter`, lifespan
- [FastAPI — Dependency Injection](dependencies.md) — `Depends()`, repository providers, and the API-key guard
- [FastAPI — Testing](testing.md) — `TestClient` and `dependency_overrides`
- [pydantic/pydantic.md](../pydantic/pydantic.md) — Pydantic is FastAPI's validation and serialisation engine
- [Uvicorn & Ports](../uvicorn.md) — the ASGI server that binds a port and actually serves the app
- [asyncio.md](../../language/concurrency/asyncio.md) — FastAPI is ASGI-native; endpoint functions can be `async def`
- [aiohttp.md](../aiohttp.md) — the HTTP *client* side of the boundary; keep outbound fetches in a pure function and the endpoint thin
