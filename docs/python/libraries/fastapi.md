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

## Three building blocks

FastAPI coordinates three components:

| Component | Role |
|-----------|------|
| **Starlette** | ASGI routing, `Request`/`Response` objects, middleware, WebSockets |
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

## What FastAPI doesn't include

No ORM, no migrations, no admin UI, no project layout opinion. It does one thing: Python functions ↔ HTTP API, with the glue (validation, serialisation, DI, docs) handled from annotations.

## Related

- [repository-di.md](../language/objects/repository-di.md) — manual DI with Protocol + `__init__` injection; the pattern `Depends()` extends
- [pydantic/pydantic.md](pydantic/pydantic.md) — Pydantic is FastAPI's validation and serialisation engine
- [asyncio.md](../language/concurrency/asyncio.md) — FastAPI is ASGI-native; endpoint functions can be `async def`
