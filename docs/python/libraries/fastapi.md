---
tags:
  - concurrency
  - design-patterns
  - typing
quiz: core
---

# FastAPI

FastAPI maps Python functions to HTTP endpoints. Its core idea: **type annotations are the single source of truth** — FastAPI reads them at decoration time and derives parsing, validation, serialisation, and API documentation automatically.

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

## Testing — override the dependency, touch no DB

`app.dependency_overrides` maps a provider to a replacement. Point `get_trade_repo` at an in-memory fake and the whole app runs against it — no database, real routing/validation/serialisation:

```python
def test_get_trade():
    fake = InMemoryTradeRepository()
    fake.save(Trade(id=42, symbol="BTC", status="OPEN"))
    app.dependency_overrides[get_trade_repo] = lambda: fake

    resp = TestClient(app).get("/trades/42")

    assert resp.json()["symbol"] == "BTC"
    app.dependency_overrides.clear()   # or reset in a fixture teardown
```

Both implementations satisfy the same `TradeRepository` Protocol, so nothing else changes. Prefer a [fake over a mock](../language/objects/repository-di.md) — it exercises the endpoint against correct behaviour.

## What FastAPI doesn't include

No ORM, no migrations, no admin UI, no project layout opinion. It does one thing: Python functions ↔ HTTP API, with the glue (validation, serialisation, DI, docs) handled from annotations.

## Related

- [repository-di.md](../language/objects/repository-di.md) — manual DI with Protocol + `__init__` injection; the pattern `Depends()` extends
- [pydantic/pydantic.md](pydantic/pydantic.md) — Pydantic is FastAPI's validation and serialisation engine
- [asyncio.md](../language/concurrency/asyncio.md) — FastAPI is ASGI-native; endpoint functions can be `async def`
