# Configuration

ColdReach is configured via environment variables. Copy `.env.example` to `.env` and edit:

```bash
cp .env.example .env
```

All variables are **optional** — the defaults work out of the box with SQLite and no Docker services.

---

## Database

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `COLDREACH_DATABASE_URL` | `sqlite+aiosqlite:///./coldreach.db` | SQLAlchemy async database URL |

To switch to PostgreSQL (requires `docker compose up postgres`):

```env
COLDREACH_DATABASE_URL=postgresql+asyncpg://coldreach:coldreach_dev@localhost:5433/coldreach
```

!!! note
    PostgreSQL requires the `postgres` extra: `pip install coldreach[postgres]`

---

## Cache

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `COLDREACH_REDIS_URL` | `redis://localhost:6380/0` | Redis connection URL |
| `COLDREACH_CACHE_TTL_DAYS` | `7` | Cache expiry in days |

ColdReach uses a two-layer cache:

1. **SQLite** (always-on, stored at `~/.coldreach/cache.db`) — works with no Docker
2. **Redis** (optional, requires `docker compose up redis`) — faster reads, shared across processes

If Redis is unavailable, ColdReach falls back to SQLite silently.

---

## Docker service URLs

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `COLDREACH_SEARXNG_URL` | `http://localhost:8088` | SearXNG metasearch endpoint |
| `COLDREACH_REACHER_URL` | `http://localhost:8083` | Reacher SMTP service endpoint |
| `COLDREACH_SPIDERFOOT_CONTAINER` | `coldreach-spiderfoot` | SpiderFoot Docker container name |
| `COLDREACH_THEHARVESTER_CONTAINER` | `coldreach-theharvester` | theHarvester Docker container name |

If a service URL is unreachable, that source is automatically skipped (SKIP status, no error).

---

## LLM (optional)

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `COLDREACH_GROQ_API_KEY` | _(not set)_ | Groq API key for LLM features |

This is the **only paid/external key** in ColdReach. It's completely optional.

Get a free key (no credit card required) at [console.groq.com](https://console.groq.com).

Unlocks:

- Personalized cold email drafts
- Subject line A/B variants
- Company summary from crawled content

Leave this unset to run ColdReach with zero external dependencies.

---

## Verification behaviour

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `COLDREACH_SMTP_TIMEOUT` | `10` | SMTP connection timeout (seconds) |
| `COLDREACH_DNS_TIMEOUT` | `5.0` | DNS resolver timeout (seconds) |
| `COLDREACH_MAX_CONCURRENT_SOURCES` | `5` | Max parallel source fetches |
| `COLDREACH_REQUEST_DELAY_SECONDS` | `1.0` | Delay between requests (rate limiting) |

---

## Scoring display

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `COLDREACH_MIN_CONFIDENCE_TO_DISPLAY` | `20` | Hide emails below this score in default output |

Emails below this threshold are found and cached — they just aren't shown unless you pass `--all`.

---

## Full `.env.example`

```env
# ── Database ──────────────────────────────────────────────────────────────────
COLDREACH_DATABASE_URL=sqlite+aiosqlite:///./coldreach.db
# COLDREACH_DATABASE_URL=postgresql+asyncpg://coldreach:coldreach_dev@localhost:5433/coldreach

# ── Cache (Redis) ─────────────────────────────────────────────────────────────
COLDREACH_REDIS_URL=redis://localhost:6380/0
COLDREACH_CACHE_TTL_DAYS=7

# ── Docker Service URLs ───────────────────────────────────────────────────────
COLDREACH_SEARXNG_URL=http://localhost:8088
COLDREACH_REACHER_URL=http://localhost:8083
COLDREACH_SPIDERFOOT_CONTAINER=coldreach-spiderfoot
COLDREACH_THEHARVESTER_CONTAINER=coldreach-theharvester

# ── LLM — Groq API (Optional) ────────────────────────────────────────────────
# COLDREACH_GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# ── Verification Behaviour ────────────────────────────────────────────────────
COLDREACH_SMTP_TIMEOUT=10
COLDREACH_DNS_TIMEOUT=5.0
COLDREACH_MAX_CONCURRENT_SOURCES=5
COLDREACH_REQUEST_DELAY_SECONDS=1.0

# ── Scoring ───────────────────────────────────────────────────────────────────
COLDREACH_MIN_CONFIDENCE_TO_DISPLAY=20
```
