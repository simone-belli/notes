# Python — Libraries / FastAPI

Building an HTTP API from type annotations: the request/response contract, how the app is assembled, what gets injected per request, and how to test the whole pipeline in-process.

:material-text-box-outline: **[App Structure](app-structure.md)**
:   Building blocks, the request lifecycle, `APIRouter`, lifespan events, and the server/client boundary

:material-text-box-outline: **[Dependency Injection](dependencies.md)**
:   `Depends()` as deferred wiring, repository providers typed as Protocols, and an API-key guard

:material-text-box-outline: **[FastAPI](fastapi.md)**
:   Annotations as the contract: path/query/body params, `response_model`, and generated OpenAPI docs

:material-text-box-outline: **[Testing](testing.md)**
:   `TestClient` in-process, mapping params to client arguments, and `dependency_overrides` for fakes
