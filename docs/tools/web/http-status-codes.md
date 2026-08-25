# HTTP Status Codes

Every HTTP response carries a three-digit **status code** + reason phrase (`200 OK`, `404 Not Found`) — the server's one-number verdict on the [request](http-request.md). The first digit is the **class**.

!!! note "4xx vs 5xx"
    **4xx blames the caller** (the request was bad), **5xx blames the server** (the request was fine, the server failed). This drives retry logic: repeating a 4xx unchanged is pointless; many 5xx are transient and worth a retry.

## The five classes

| Class | Meaning | Gist |
|-------|---------|------|
| `1xx` | Informational | Provisional, rarely seen directly |
| `2xx` | Success | Request understood and fulfilled |
| `3xx` | Redirection | More action needed — look elsewhere |
| `4xx` | Client error | The request was bad |
| `5xx` | Server error | The server failed |

## Codes you actually meet

**2xx**

- `200 OK` — default success, result in the body.
- `201 Created` — `POST`/`PUT` created a resource; often a `Location` header points to it.
- `202 Accepted` — accepted for async work, not done yet.
- `204 No Content` — success with no body (common for `DELETE`).

**3xx**

- `301 Moved Permanently` / `302 Found` — permanent vs temporary redirect.
- `304 Not Modified` — cache validators (`ETag`/`If-None-Match`) still valid; no body sent.
- `307` / `308` — like `302`/`301` but preserve the HTTP method (won't turn a `POST` into a `GET`).

**4xx**

- `400 Bad Request` — malformed/invalid request (e.g. bad JSON).
- `401 Unauthorized` — not **authenticated** (log in). Should carry a `WWW-Authenticate` header.
- `403 Forbidden` — authenticated but not **authorised**.
- `404 Not Found` — no such resource.
- `405 Method Not Allowed` — URL exists, not for that verb.
- `409 Conflict` — clashes with current state (duplicate, version conflict).
- `422 Unprocessable Entity` — syntactically valid but semantically wrong; [FastAPI](../../python/libraries/fastapi/fastapi.md)/Pydantic returns this on validation failure.
- `429 Too Many Requests` — rate-limited; often a `Retry-After` header.

**5xx**

- `500 Internal Server Error` — generic unhandled failure on the server.
- `502 Bad Gateway` — a proxy got an invalid response from upstream.
- `503 Service Unavailable` — temporarily down/overloaded; may carry `Retry-After`.
- `504 Gateway Timeout` — upstream didn't respond in time.

!!! tip "401 vs 403"
    **401 = "I don't know who you are"** (missing/bad credentials → authenticate). **403 = "I know who you are, and you still can't"** (authenticated, but forbidden).

## Retry rules of thumb

- **4xx** — don't retry unchanged; fix the request. Exception: `429` (back off, then retry after the delay).
- **5xx** — often transient (`502`/`503`/`504`); retry with exponential backoff. `500` is ambiguous — retry cautiously.
- The [aiohttp](../../python/libraries/aiohttp.md) retry helper encodes exactly this: retry on `status >= 500`, give up on `4xx`.
