# URL Shortener — Implementation Plan

## System Design (The "Why" Before The "How")

### Functional Requirements
- Shorten a long URL → generate a unique short code
- Redirect short code → original URL
- Click analytics (total clicks, last clicked timestamp)
- User accounts (register/login, links tied to a user)
- Link expiration (default 30 days)

### Non-Functional Requirements
- **Fast redirects:** Redirects must be near-instant (cache layer)
- **Low latency:** Users should not wait for analytics writes
- **Scalable cache:** Redis for hot URLs
- **Collision resistant:** Base62 encoding with retry logic

### Architecture Diagrams

**Cache-Aside Redirect Flow:**
```
Request → Redis?
  ├── Hit  → Return URL (fast path)
  └── Miss → PostgreSQL → Update Redis → Return URL (slow path)
```

**Analytics Flow (Non-Blocking):**
```
Redirect Request → Return redirect immediately to user
                 → (background task) → Increment click count in DB
```

---

## Tech Stack
- **FastAPI** (synchronous first, async migration later)
- **PostgreSQL + SQLAlchemy 2.0** (sync engine first)
- **Redis** (cache + rate limiting + TTL expiration)
- **Alembic** (database migrations)
- **Docker + Docker Compose** (containerization)

---

## Build Order (Every Milestone = A Working App)

### Milestone 1 — Core Foundation
> *After this: You have a working URL shortener with auth and database.*

- [ ] Project setup (folder structure, config, .env)
- [ ] PostgreSQL + SQLAlchemy (synchronous) + Alembic
- [ ] User model + auth (register/login with JWT)
- [ ] URL model (original_url, short_code, user_id, created_at, expires_at, click_count)
- [ ] Base62 shortener utility with collision retry
- [ ] CRUD routes: create short URL, list user's URLs, delete URL

### Milestone 2 — Redirect + Caching
> *After this: Your redirects are lightning fast with Redis cache-aside.*

- [ ] Redirect endpoint (`GET /{short_code}` → 307 redirect)
- [ ] Install and connect Redis
- [ ] Implement cache-aside pattern (check Redis first, fallback to DB, populate cache)
- [ ] Link expiration (TTL in Redis, `expires_at` check in DB)

### Milestone 3 — Analytics + Background Tasks
> *After this: Every click is tracked without slowing down the user.*

- [ ] Click analytics (total_clicks, last_clicked_at)
- [ ] FastAPI BackgroundTasks to update analytics asynchronously
- [ ] Analytics endpoint (get click stats for a URL)

### Milestone 4 — Rate Limiting
> *After this: Your API is protected from abuse.*

- [ ] Redis-based rate limiter (sliding window or token bucket)
- [ ] Implement as FastAPI middleware
- [ ] Return proper 429 Too Many Requests responses

### Milestone 5 — Docker + Deployment + README
> *After this: Your entire app runs with a single `docker-compose up`.*

- [ ] Dockerfile for the FastAPI app
- [ ] docker-compose.yml (FastAPI + PostgreSQL + Redis)
- [ ] Professional README with architecture diagrams
- [ ] "Future Scaling" section (Phase 3 — discuss, don't build)

### Milestone 6 — Async Migration
> *After this: You understand WHY async exists by having felt the sync version first.*

- [ ] Migrate SQLAlchemy engine to async (`create_async_engine`)
- [ ] Migrate all database operations to use `AsyncSession`
- [ ] Migrate route functions to `async def`

---

## Phase 2 — If Time Remains
- Custom/vanity short codes
- API keys for programmatic access
- 3-5 targeted unit tests (base62 logic, cache-aside, rate limiter)
- Structured logging + error handling
- OpenAPI docs with request/response examples

## Phase 3 — README Discussion Only (Don't Build)
Write a "Future Scaling" section covering:
- Consistent hashing for horizontal DB sharding
- Kafka / Redis Streams for high-volume click analytics
- Read replicas for PostgreSQL
- Redis Cluster for cache scaling
- CDN in front of redirects

> **Interview answer for "Why not Kafka?":** Current traffic doesn't justify the operational complexity. At higher click volumes, you'd stream analytics events into Kafka instead of writing counters directly to Postgres on every redirect.

---

## Project Structure
```
url-shortener/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   └── security.py
│   ├── middleware/
│   │   └── rate_limit.py
│   ├── cache/
│   │   └── redis.py
│   ├── routers/
│   │   ├── urls.py
│   │   ├── analytics.py
│   │   └── auth.py
│   ├── schemas/
│   │   └── url.py
│   ├── models/
│   │   ├── url.py
│   │   └── user.py
│   ├── services/
│   │   └── url_service.py
│   └── utils/
│       └── shortener.py
├── alembic/
├── tests/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

> [!IMPORTANT]
> No `repositories/` layer. Services talk directly to SQLAlchemy. Every layer must earn its existence.
