---
tags:
  - cli
---

# curl

`curl` ("client URL") makes HTTP requests from the terminal — the universal way to hit an API by hand: test an endpoint, inspect headers, reproduce a bug, script a health check. It's a **client** (sends a request, prints the response), the shell counterpart to a browser or Python [`httpx`](../../python/libraries/httpx.md)/`requests`.

## Mental model

Every invocation is one [HTTP request](http-request.md). Flags set its four parts; the **response body** goes to stdout (status line and headers are *not* shown unless you ask):

- **method** — `-X GET/POST/…` (defaults to `GET`, or `POST` when a body is sent)
- **URL** — the positional argument (`?k=v` query string lives here)
- **headers** — `-H "Name: value"`, repeatable
- **body** — `-d`, `--json`, or `-F`

## Flags that matter

```bash
curl https://api.example.com/trades        # GET, body → stdout
curl -i https://.../trades                 # include response headers
curl -I https://.../trades                 # HEAD — headers only, no body
curl -sS https://.../trades                # silent, but still show errors
curl -L https://example.com                # follow redirects (3xx)
curl -f https://.../x                       # fail (exit ≠0) on HTTP ≥400
curl -v https://.../x                       # verbose: full request + response
curl -o out.json https://.../x             # write body to a file
```

- `-v` shows exactly what went over the wire (`>` sent, `<` received) — the go-to for debugging.
- `-L` follows a `Location` redirect; curl does **not** by default.

## Sending data

```bash
curl --json '{"symbol":"BTC"}' https://.../trades      # POST + JSON headers (curl ≥7.82)
curl -d '{"symbol":"BTC"}' -H "Content-Type: application/json" https://.../trades
curl -d "user=me&pw=secret" https://.../login          # form-encoded
curl -F "file=@data.csv" https://.../upload            # multipart upload
```

- `-d` implies `POST` + `Content-Type: application/x-www-form-urlencoded`.
- `--json` implies `POST` and sets `Content-Type`/`Accept` to `application/json` — one flag to hit a JSON API.
- `@file` reads a value from a file (`-d @body.json` sends the file as the body).

## Auth

```bash
curl -H "Authorization: Bearer $TOKEN" https://.../me   # bearer token
curl -u user:pass https://.../me                        # HTTP basic auth
```

!!! warning "Exit code reflects transport, not HTTP"
    curl exits **0** whenever the request completes — *even on a `500`* — because the round-trip succeeded; non-zero means it couldn't connect (DNS, TLS, refused). In scripts add `-f` to fold an HTTP [status](http-status-codes.md) ≥400 into a non-zero exit, and check for the code with `-w "%{http_code}\n"`.

## Handy

- `curl -s .../x | jq` — pipe JSON into [`jq`](../jq.md) for readable output.
- `-w "%{http_code}\n"` — print just the status code (or timing/size) after the body.

## Related

- [HTTP Status Codes](http-status-codes.md) — the codes curl reports; `-f` keys off ≥400
- [Uvicorn & Ports](../../python/libraries/uvicorn.md) — the server side curl talks to (`localhost:8000`)
