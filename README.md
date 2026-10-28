# URL Shortener API

An async URL shortener built with FastAPI, PostgreSQL, and Redis. It supports authenticated link management, expiring redirects, cached redirect lookups, click analytics, and an atomic Redis token-bucket rate limiter.

## Features

- JWT authentication and Argon2 password hashing.
- Base62 short codes with bounded collision retries and a database uniqueness constraint.
- PostgreSQL as the source of truth; Redis cache-aside redirects with expiry-aware TTLs.
- Atomic click-count updates in PostgreSQL after redirects.
- Redis Lua token-bucket limits for authentication, API, and redirect routes.
- Liveness and dependency-backed readiness endpoints at `/health/live` and `/health/ready`.
- Docker Compose stack for local PostgreSQL, Redis, and the API.
- Responsive same-origin web dashboard for registration, login, link management, copying, and analytics.

## Run locally

Install Docker Desktop and start the Docker daemon. From the repository root:

```powershell
$env:SECRET_KEY = "replace-with-a-random-secret-of-at-least-32-characters"
$env:POSTGRES_PASSWORD = "replace-with-a-random-alphanumeric-database-password"
docker compose up --build
```

Compose runs migrations before starting the API. Open the dashboard at <http://localhost:8000> or API documentation at <http://localhost:8000/docs>. PostgreSQL and Redis are accessible only to containers in the Compose network. Keep both passwords out of Git; set them as environment variables on each machine before starting Compose. If a PostgreSQL volume already exists, changing `POSTGRES_PASSWORD` in Compose does not change that database's existing password.

For a local Python environment, set `DATABASE_URL`, `REDIS_URL`, and `SECRET_KEY`, install `requirements.txt`, run `alembic upgrade head`, and start the service with `uvicorn app.main:app --reload`.

## Verify

Run unit and API tests:

```powershell
$env:DATABASE_URL = "postgresql://test:test@127.0.0.1:5432/test"
$env:REDIS_URL = "redis://127.0.0.1:6379/0"
$env:SECRET_KEY = "local-test-secret-that-is-at-least-32-characters"
python -m pytest -q
```

The API tests replace database and Redis calls with controlled test doubles. To exercise real dependencies and migrations, run `docker compose up --build` and use the interactive API docs or add a service-backed test profile.

## Load test

With the app running, install [k6](https://grafana.com/docs/k6/latest/set-up/install-k6/) and run:

```powershell
k6 run k6/load_test.js
```

The script reports successful redirect latency and throughput separately from `429` responses. The redirect token bucket is shared by client IP, so this load profile intentionally encounters the configured limiter. For an app-capacity benchmark, set `RATE_LIMIT_ENABLED=false` only in an isolated local benchmark environment, restart the app, run k6, then restore rate limiting. Record the app version, CPU and memory, worker count, dependency versions, cache warmup state, VU/stage profile, successful redirects per second, p95 latency, and failure rate with every result. Do not report requests per second that include rejected requests as successful redirect throughput.

## Resume description

> Built an async URL-shortening API with FastAPI, PostgreSQL, and Redis, adding JWT-protected link management, expiry-aware cached redirects, atomic click analytics, and a Lua-based token-bucket rate limiter.

Add benchmark figures only after collecting and saving repeatable k6 results with the environment and success rate stated.
