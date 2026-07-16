# URL Shortener
A URL shortener built with FastAPI, featuring authenticated URL management, Redis-backed redirects, click analytics, and rate limiting.

## Features
- Core: Users can create, list, and delete short URLs.
- Short URL creation logic: Base62 shortener utility with collision retry.
- Fast redirects: Redis cache-aside pattern for redirect metadata, with link expiration.
- Analytics: Click count and last-click timestamp are updated using FastAPI BackgroundTasks.
- Rate limiting: Policy-based token bucket rate limiting using Redis and a Lua script, implemented as middleware.
- Data validation: Inputs are validated using Pydantic schemas.
- Security: JWT authentication for protected routes.
- Database: Relational PostgreSQL database modeled with SQLAlchemy.

## Tech Stack
- Python
- FastAPI
- SQLAlchemy
- PostgreSQL
- Redis
- Docker

## Architecture
```text
Client
  |
  | HTTP
  v
FastAPI app
  |
  |-- JWT auth protects URL management and analytics routes
  |
  |-- Redis / Upstash
  |     |-- Cache-aside redirects: short_code -> URL metadata
  |     |-- Token-bucket rate limiting with Lua script
  |
  |-- BackgroundTasks
  |     |-- Updates click_count and last_clicked_at after redirect
  |
  v
SQLAlchemy ORM
  |
  v
PostgreSQL / Neon
```

### Redirect Flow
```text
GET /{short_code}
  |
  |-- Check Redis cache
  |     |-- Hit: redirect immediately and update analytics in background
  |     |-- Miss: query PostgreSQL
  |
  |-- Validate link expiry
  |-- Store redirect metadata in Redis with TTL
  |-- Return RedirectResponse
```

### Rate Limiting Flow
```text
Request
  |
  v
Rate limit middleware
  |
  |-- Classify route policy: auth, API, or redirect
  |-- Run Redis Lua token-bucket script atomically
  |-- Allow request or return 429 Too Many Requests
  |
  v
FastAPI route handler
```

## Installation
1. Create and activate a virtual environment:
```bash
python -m venv venv
venv\Scripts\activate
```

2. Create a `.env` file and add your environment variables:
```env
DATABASE_URL=...
SECRET_KEY=...
REDIS_URL=...
```

3. Install the required dependencies:
```bash
pip install -r requirements.txt
```

4. Run database migrations:
```bash
alembic upgrade head
```

5. Start the FastAPI development server:
```bash
fastapi dev app/main.py
```

## Dockerized Local Deployment
This application is containerized with Docker and can run locally against managed PostgreSQL (Neon) and Redis (Upstash) services.

- Docker packages the application, Python runtime, and dependencies into a portable container.
- PostgreSQL (Neon) is used as the source of truth.
- Redis (Upstash) is used for redirect caching and token-bucket rate limiting.

Build the Docker image:
```bash
docker build -t url-shortener .
```

Run the container locally:
```bash
docker run -p 8000:8000 --env-file .env url-shortener
```

Open the API docs:
```text
http://127.0.0.1:8000/docs
```

## Cloud Run Deployment Target
The app is designed to be deployable to Google Cloud Run using the Dockerfile, but this deployment is optional and requires an active Google Cloud billing account.

```bash
gcloud auth login
gcloud config set project <your-project-id>
gcloud run deploy url-shortener --source . --region us-east1 --allow-unauthenticated
```

## Future Scaling
- CDN or edge caching in front of redirects for globally popular links.
- Redis Cluster for scaling cache and rate-limit state.
- PostgreSQL read replicas for heavy read traffic.
- Kafka or Redis Streams for high-volume click analytics.
- Gateway-level rate limiting through Cloudflare, Nginx, or an API gateway.