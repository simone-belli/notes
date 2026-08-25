---
tags:
  - testing
---

# FastAPI — Testing

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

## Override the dependency, touch no DB

`app.dependency_overrides` maps a provider to a replacement. Point [`get_trade_repo`](dependencies.md#injecting-a-repository-same-as-constructor-injection) at an in-memory fake and the whole app runs against it — no database, real routing/validation/serialisation:

```python
def test_get_trade():
    fake = InMemoryTradeRepository()
    fake.save(Trade(id=42, symbol="BTC", status="OPEN"))
    app.dependency_overrides[get_trade_repo] = lambda: fake

    resp = TestClient(app).get("/trades/42")

    assert resp.json()["symbol"] == "BTC"
    app.dependency_overrides.clear()   # dict lives on app — clear or it leaks
```

Both implementations satisfy the same `TradeRepository` Protocol, so nothing else changes. Prefer a [fake over a mock](../../language/objects/repository-di.md) — it exercises the endpoint against correct behaviour. `dependency_overrides` is a plain dict on the `app`, so wrap client + reset in a [pytest fixture](../../tooling/testing/fixtures.md) to keep tests isolated:

```python
@pytest.fixture
def client():
    with TestClient(app) as c:        # lifespan runs
        yield c
    app.dependency_overrides.clear()  # teardown resets overrides
```

For a test that must `await` itself, use `httpx.AsyncClient` with an Asynchronous Server Gateway Interface (ASGI) transport — `ASGITransport(app=app)` — instead; `TestClient` (sync) covers nearly all endpoint tests.

## Related

- [Dependency Injection](dependencies.md) — the `Depends()` providers these tests override
- [fixtures.md](../../tooling/testing/fixtures.md) — pytest fixtures for wrapping `TestClient` and resetting overrides
- [testing-strategy.md](../../tooling/testing/testing-strategy.md) — where in-process endpoint tests sit relative to unit and contract tests
