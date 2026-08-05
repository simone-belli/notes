---
tags:
  - config
  - packaging
---

# Render — deploying a web service

Render is a Platform-as-a-Service (PaaS): connect a Git repo, and on every push to a chosen branch it **builds** your app and **runs** it behind a public URL with TLS. For a Python web service the whole thing is configuration — the app does the work, Render just supplies a build command, a start command, a Python version, and environment variables.

!!! tip "Golden rule: reproduce production locally *before* you touch Render"
    Debugging path resolution, seeding, or [Poetry](../python/tooling/poetry.md) on a remote box with multi-minute rebuild cycles is miserable. Recreate the deploy conditions on your machine first — empty data dir, `ENVIRONMENT=production`, **no `.env` file**, boot with [uvicorn](../python/libraries/uvicorn.md), hit a real endpoint. Only once that's green do you go remote. On Render you should be debugging *Render*, not your code.

## Before deploying

- Merge to the **branch Render deploys from** (usually `main`, behind [green CI](../git/github-actions.md)) — the deployed branch is the source of truth.
- Verify a **cold start** locally: from an empty data dir, does the app boot and serve? A [lifespan](../python/libraries/fastapi.md#lifespan-startup-and-shutdown) that seeds on startup makes this reproducible.
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

Keep it **one worker** (the default) if startup seeds shared state — a single process makes that [lifespan](../python/libraries/fastapi.md#lifespan-startup-and-shutdown) seed race-free.

**3. Python version** — set the `PYTHON_VERSION` env var (e.g. `3.12.7`) to match CI and your lockfile's resolution.

!!! warning "`.python-version` is often gitignored"
    Render normally reads a committed `.python-version`, but that file is commonly in `.gitignore` — so it isn't in the repo and Render falls back to a default that may not match your lockfile. Set `PYTHON_VERSION` in the dashboard instead.

**4. Environment variables & secrets** — your `.env` is (correctly) gitignored, so on Render these come from the dashboard. [`pydantic-settings`](../python/libraries/pydantic/pydantic-settings.md) reads OS env directly and maps field names case-insensitively. Typical set:

- A **writable data path** — Render checks the repo out to `/opt/render/project/src`, so `/opt/render/project/src/data` works. It **resets on each redeploy**, which is fine if startup reseeds.
- The **API key** (mark it *secret* so it's write-only in the UI).
- `ENVIRONMENT=production`, `LOG_LEVEL=INFO`, etc.

See [Environment Variables](env-vars.md) for the underlying model.

## First deploy — verify in order

1. **Build succeeds** — the classic failure is *Poetry not found*, which the `pip install poetry` build command fixes.
2. **Startup logs fire** — seed/init lines prove the lifespan ran and populated state.
3. **Endpoints respond** — open `/docs`, authorise, call the real routes; expect non-empty results and no `500`s.
4. **Outbound calls may be blocked** — third-party APIs that geofence datacenter IPs can return [`403`/`451`](http-status-codes.md). Expected, not your bug — don't make it the headline of a demo.

## Free-tier realities

- **Spin-down** after ~15 min idle; the next request cold-starts in ~30–50s. Fine for a portfolio link.
- **Ephemeral disk** — anything written at runtime vanishes on the next redeploy/restart. Design for a read-mostly (reseed-on-boot) contract.
- FastAPI has no `/` route by default, so the root shows `404`. Harmless (the health check only needs the port to answer), but a trivial `/health → 200` reads cleaner to a visitor who lands on the root.

## Infrastructure as code: `render.yaml`

Everything above is dashboard clicking. A committed **`render.yaml` Blueprint** declares the build/start commands and env vars (secrets still set in the dashboard) — versioned, reviewable Infrastructure-as-Code.

!!! note "Dashboard first, Blueprint second"
    Get the first deploy live via the dashboard, then convert to `render.yaml` once it works — otherwise you're debugging Blueprint syntax and your app simultaneously.

## Related

- [Uvicorn & Ports](../python/libraries/uvicorn.md) — the ASGI server and the `$PORT` / `0.0.0.0` binding Render requires
- [FastAPI](../python/libraries/fastapi.md) — the app being served; its lifespan seeds state on boot
- [Poetry](../python/tooling/poetry.md) — bootstrapped in the build command since Render's runtime ships `pip`
- [pydantic-settings](../python/libraries/pydantic/pydantic-settings.md) — reads the dashboard env vars as typed config
- [Environment Variables](env-vars.md) — scopes, `.env`, and secrets
