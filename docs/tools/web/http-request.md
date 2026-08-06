# HTTP Requests

HyperText Transfer Protocol (HTTP) is a **request–response** protocol: a client sends a *request message*, the server replies with a *response*. In HTTP/1.1 a request is **just text** over a Transmission Control Protocol (TCP) connection — every client ([curl](curl.md), Python `requests`/[aiohttp](../../python/libraries/aiohttp.md), a browser) is a convenience layer that formats the same bytes.

## Anatomy of a request

Four parts, in order:

```
POST /api/trades?symbol=BTC HTTP/1.1      ← 1. request line: METHOD  target  version
Host: api.example.com                     ← 2. headers, one per line
Content-Type: application/json
Content-Length: 18
                                          ← 3. blank line — mandatory, ends the headers
{"symbol": "BTC"}                         ← 4. body (optional)
```

- **Request line** — `METHOD  request-target  HTTP-version`, single spaces. The target is the *path + query string*; the host lives in the `Host` header, not here.
- **Headers** — `Name: value` lines, case-insensitive names.
- **Blank line** — a bare `CRLF` (`\r\n`). Required; everything after it is the body. Line endings are CRLF, not `\n`.
- **Body** — optional; present for `POST`/`PUT`/`PATCH`, normally absent for `GET`/`DELETE`.

## Methods

| Method | Intent | Idempotent? | Safe? |
|--------|--------|-------------|-------|
| `GET` | Read | Yes | Yes |
| `POST` | Create / submit / trigger | No | No |
| `PUT` | Replace wholesale | Yes | No |
| `PATCH` | Partial update | No | No |
| `DELETE` | Remove | Yes | No |
| `HEAD` | `GET` headers only, no body | Yes | Yes |
| `OPTIONS` | Ask what's allowed (CORS) | Yes | Yes |

- **Safe** = read-only, no state change. **Idempotent** = repeating it has the same effect as doing it once.
- These are conventions the server is trusted to honour, not enforced by the protocol.

!!! warning "Don't blindly retry a POST"
    `PUT`/`DELETE` are idempotent, so retrying after a timeout is safe. `POST` usually isn't — a blind retry can create two orders or double-charge a card. Use an idempotency key if you must retry.

## Key headers

- **`Host`** — the domain. **Mandatory in HTTP/1.1** (one IP serves many sites).
- **`Content-Type`** — media type of the body you're *sending* (`application/json`, `application/x-www-form-urlencoded`, `multipart/form-data`).
- **`Content-Length`** — body size in bytes; usually set for you.
- **`Accept`** — media type you *want back* (content negotiation).
- **`Authorization`** — credentials: `Bearer <token>` or `Basic <base64(user:pass)>`.

!!! note "Content-Type vs Accept"
    **`Content-Type` describes the body you send up; `Accept` describes the body you want back down.** A request can carry both.

## Query strings

`GET` parameters go after `?`: `/search?q=bitcoin&limit=10`. `&` separates pairs, `=` joins key and value. Special characters must be **percent-encoded** (space → `%20`); clients do this for you. Query strings leak into logs — put secrets in `Authorization`, never the URL.

## Body formats

- **JSON** (`application/json`) — the modern default: `{"symbol": "BTC"}`.
- **Form-encoded** (`application/x-www-form-urlencoded`) — `symbol=BTC&qty=5`, query-string syntax in the body.
- **Multipart** (`multipart/form-data`) — file uploads.

The `Content-Type` must match the actual body, or you get a `400`.

## Sending one

The same request via three interfaces — all produce identical bytes on the wire:

```bash
curl -X POST https://api.example.com/trades \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $TOKEN" \
     -d '{"symbol":"BTC"}'
```

```python
import requests

resp = requests.post(
    "https://api.example.com/trades",
    json={"symbol": "BTC"},          # sets body + Content-Type: application/json
    headers={"Authorization": f"Bearer {token}"},
    params={"dryRun": "true"},       # → ?dryRun=true
    timeout=10,                      # always set one, or a hung server hangs you
)
resp.raise_for_status()              # 4xx/5xx → exception
data = resp.json()
```

## The response

Same shape in reverse: a status line (`HTTP/1.1 200 OK`) instead of a request line, then headers, blank line, body. The three-digit code is the server's verdict — see [HTTP Status Codes](http-status-codes.md).

!!! tip "HTTP/2 and HTTP/3"
    Only HTTP/1.1 is human-readable text; HTTP/2/3 use a binary, multiplexed framing you can't type by hand. The *semantics* are identical — method, target, headers, body — so the mental model and every client API stay the same.

## Related

- [curl](curl.md) — send requests from the terminal; flags map onto the four parts
- [HTTP Status Codes](http-status-codes.md) — the response side's verdict
- [aiohttp](../../python/libraries/aiohttp.md) — async HTTP client in Python
