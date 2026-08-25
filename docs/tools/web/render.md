---
tags:
  - config
  - packaging
---

# Render — deploying a web service

Render is a Platform-as-a-Service (PaaS): connect a Git repo, and on every push to a chosen branch it **builds** your app and **runs** it behind a public URL with TLS. For a Python web service the whole thing is configuration — the app does the work, Render just supplies a build command, a start command, a Python version, and environment variables.

!!! tip "Golden rule: reproduce production locally *before* you touch Render"
    Debugging path resolution, seeding, or [Poetry](../../python/tooling/poetry.md) on a remote box with multi-minute rebuild cycles is miserable. Recreate the deploy conditions on your machine first — empty data dir, `ENVIRONMENT=production`, **no `.env` file**, boot with [uvicorn](../../python/libraries/uvicorn.md), hit a real endpoint. Only once that's green do you go remote. On Render you should be debugging *Render*, not your code.

## Before deploying

- Merge to the **branch Render deploys from** (usually `main`, behind [green CI](../../git/github-actions.md)) — the deployed branch is the source of truth.
- Verify a **cold start** locally: from an empty data dir, does the app boot and serve? A [lifespan](../../python/libraries/fastapi/app-structure.md#lifespan-startup-and-shutdown) that seeds on startup makes this reproducible.
- Decide the **auth story** — if every endpoint is behind an API key, pick the demo key you'll store as a secret.

## The four settings that matter

**1. Build command** — Render's Python runtime uses `pip`, not Poetry, so bootstrap Poetry first:

```bash
pip install poetry && poetry install --only main
```

`--only main` skips the dev group — no linter/type-checker/test runner needed to *run* the server.

**2. Start command** — binding `0.0.0.0:$PORT` is non-negotiable; Render injects `$PORT` and routes to it:

```bash
poetry run uvicorn myapp.main:app --host 0.0.0.0 --port $PORT
```

Keep it **one worker** (the default) if startup seeds shared state — a single process makes that [lifespan](../../python/libraries/fastapi/app-structure.md#lifespan-startup-and-shutdown) seed race-free.

**3. Python version** — set the `PYTHON_VERSION` env var (e.g. `3.12.7`) to match CI and your lockfile's resolution.

!!! warning "`.python-version` is often gitignored"
    Render normally reads a committed `.python-version`, but that file is commonly in `.gitignore` — so it isn't in the repo and Render falls back to a default that may not match your lockfile. Set `PYTHON_VERSION` in the dashboard instead.

**4. Environment variables & secrets** — your `.env` is (correctly) gitignored, so on Render these come from the dashboard. [`pydantic-settings`](../../python/libraries/pydantic/pydantic-settings.md) reads OS env directly and maps field names case-insensitively. Typical set:

- A **writable data path** — Render checks the repo out to `/opt/render/project/src`, so `/opt/render/project/src/data` works. It **resets on each redeploy**, which is fine if startup reseeds.
- The **API key** (mark it *secret* so it's write-only in the UI).
- `ENVIRONMENT=production`, `LOG_LEVEL=INFO`, etc.

See [Environment Variables](../shell/env-vars.md) for the underlying model.

## Verifying a live service — in stages

"Live" in the Render dashboard only means the health check got a TCP answer on `$PORT` — it says nothing about whether your app works. Verify in a ladder, cheapest checks first, so a failure points at one layer instead of the whole stack. Stop at the first red stage and fix it before moving on.

**1. Build succeeded** — read the *Build* log to its end. The classic failure is *Poetry not found* (fixed by the `pip install poetry` build command); the next is a dependency that won't resolve on Render's Python version. A red build never reaches your code.

**2. Startup logs fired** — read the *Deploy/runtime* log. You want the [lifespan](../../python/libraries/fastapi/app-structure.md#lifespan-startup-and-shutdown) seed/init lines *and* uvicorn's `Uvicorn running on http://0.0.0.0:$PORT`. Common failures: app crashes on boot (missing env var, `pydantic-settings` validation error), or it binds `127.0.0.1`/a hardcoded port so Render's health check never connects and the deploy loops.

**3. The port answers** — hit the root from your machine, not the browser:

```bash
curl -i https://myapp.onrender.com/
```

Any HTTP status (even a FastAPI `404` on `/`) proves routing works. A hang or connection reset means the process isn't listening on `$PORT` — back to stage 2. A `502`/`503` from Render's edge means the app crashed *after* binding, or is still cold-starting (~30–50s on free tier — retry once).

**4. Health check is green** — `curl -i .../health` should give `200`. A trivial `/health → 200` route (see free-tier note) makes this an unambiguous "app is up" signal distinct from the root `404`.

**5. Auth behaves** — a protected route with **no** key should be `401`/`403`, and **with** the demo key `200`. Getting `200` unauthenticated means the key check isn't wired; getting `401` *with* the key means the secret in the dashboard doesn't match what you're sending (trailing newline, wrong var name — remember `pydantic-settings` matches case-insensitively but not typos).

**6. Real endpoints return real data** — open `/docs`, authorise, call the actual routes. Expect non-empty results and no `500`s. An empty-but-`200` response usually means the writable data path is wrong or the seed didn't populate it — check the data-path env var against `/opt/render/project/src/data`.

**7. State survives a restart** — trigger a *Manual Deploy → Clear build cache & deploy* (or just restart) and re-run stages 3–6. On the free tier the disk is [ephemeral](#free-tier-realities), so anything written at runtime is gone; only a reseed-on-boot contract survives. This catches "worked right after deploy, broke overnight" before a visitor does.

**8. Outbound calls** — third-party APIs that geofence datacenter IPs can return [`403`/`451`](http-status-codes.md) from Render even though they work from your laptop. Expected, not your bug — but confirm it's *that* and not a missing API-key secret, and don't make it the headline of a demo.

!!! tip "A one-liner smoke test beats clicking around"
    Chain the stages into a script — `curl` root, `/health`, an unauthenticated call (expect `401`), then an authenticated call (expect `200` + data) — and eyeball the four status codes. It reproduces the whole ladder in seconds after every redeploy. See [curl](curl.md) for `-i`, `-H`, and exit codes.

## Free-tier realities

- **Spin-down** after ~15 min idle; the next request cold-starts in ~30–50s. Fine for a portfolio link.
- **Ephemeral disk** — anything written at runtime vanishes on the next redeploy/restart. Design for a read-mostly (reseed-on-boot) contract.
- FastAPI has no `/` route by default, so the root shows `404`. Harmless (the health check only needs the port to answer), but a trivial `/health → 200` reads cleaner to a visitor who lands on the root.

## Infrastructure as code: `render.yaml`

Everything above is dashboard clicking. A committed **`render.yaml` Blueprint** declares the build/start commands and env vars (secrets still set in the dashboard) — versioned, reviewable Infrastructure-as-Code.

!!! note "Dashboard first, Blueprint second"
    Get the first deploy live via the dashboard, then convert to `render.yaml` once it works — otherwise you're debugging Blueprint syntax and your app simultaneously.

## Related

- [Uvicorn & Ports](../../python/libraries/uvicorn.md) — the ASGI server and the `$PORT` / `0.0.0.0` binding Render requires
- [FastAPI](../../python/libraries/fastapi/fastapi.md) — the app being served; its lifespan seeds state on boot
- [Poetry](../../python/tooling/poetry.md) — bootstrapped in the build command since Render's runtime ships `pip`
- [pydantic-settings](../../python/libraries/pydantic/pydantic-settings.md) — reads the dashboard env vars as typed config
- [Environment Variables](../shell/env-vars.md) — scopes, `.env`, and secrets
