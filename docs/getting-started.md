# Getting Started

---

## Option A — Simple install (once published to PyPI)

If you only need `verify` and basic `find` (no Docker, no OSINT tools):

```bash
pip install coldreach
coldreach verify john@acme.com
coldreach find --domain acme.com --quick
```

This works immediately with zero setup. Docker services are optional — ColdReach detects unavailable services and skips them automatically.

---

## Option B — Full install from source

For the complete stack (SMTP verification, deep OSINT, caching):

### Prerequisites

- Python 3.11 or newer
- Docker + Docker Compose
- Git

### Step 1 — Clone and run setup

```bash
git clone https://github.com/dhruvmojila/coldreach.git
cd coldreach
./scripts/setup.sh
```

`setup.sh` does three things:

1. Clones **theHarvester** (OSINT tool) into `./theHarvester/`
2. Clones **SpiderFoot** (deep OSINT) into `./spiderfoot/`
3. Copies `.env.example` → `.env` (if `.env` doesn't exist yet)

!!! note
`theHarvester/` and `spiderfoot/` are gitignored — they're external tools
built locally via Docker, not committed to this repo.

---

### Step 2 — Configure (optional)

Open `.env` and review the defaults. Everything works out of the box — no API keys required.

```bash
# The only setting you might want to add (free at console.groq.com)
COLDREACH_GROQ_API_KEY=gsk_xxxx   # unlocks LLM email personalization
```

See the full [Configuration reference](configuration.md) for all options.

---

### Step 3 — Start Docker services

```bash
# First time only — build images for the OSINT tools
docker compose build spiderfoot theharvester

# Start all services in the background
docker compose up -d
```

Check that everything is healthy:

```bash
docker compose ps
```

You should see all services as `healthy` or `running`. If you only want the core verification stack (lighter):

```bash
docker compose up redis reacher -d
```

### Docker services

| Service        | Port     | Purpose                                               |
| -------------- | -------- | ----------------------------------------------------- |
| `postgres`     | **5433** | Persistent storage (SQLite is the default — optional) |
| `redis`        | **6380** | Result cache with 7-day TTL                           |
| `searxng`      | **8088** | Metasearch across 40+ search engines                  |
| `reacher`      | **8083** | SMTP email verification (Rust microservice)           |
| `spiderfoot`   | **5001** | Deep OSINT REST API                                   |
| `theharvester` | **5050** | Multi-source email/host harvester                     |

!!! tip "Ports are offset from defaults"
Ports are shifted to avoid conflicts with common local dev services
(postgres :5432, redis :6379, searxng :8080).

---

### Step 4 — Install ColdReach

=== "pip"

    ```bash
    pip install coldreach
    ```

=== "uv (recommended for dev)"

    ```bash
    pip install uv
    uv sync
    ```

=== "editable (for contributors)"

    ```bash
    pip install uv
    uv sync --all-extras --dev
    ```

Verify the install:

```bash
coldreach --version
```

---

### Step 5 — Try it

### Verify a single email

```bash
coldreach verify john@acme.com
```

With full SMTP + platform check (slower, more accurate):

```bash
coldreach verify john@acme.com --holehe
```

### Find emails for a domain

```bash
# Quick mode — skips slow OSINT sources (theHarvester, SpiderFoot)
coldreach find --domain stripe.com --quick

# Full discovery
coldreach find --domain stripe.com

# Target a specific person
coldreach find --domain stripe.com --name "Patrick Collison"
```

### JSON output (for scripting)

```bash
coldreach find --domain stripe.com --json | jq '.emails[].email'
```

### Cache management

```bash
coldreach cache list          # show all cached domains
coldreach cache stats         # total / valid / expired counts
coldreach cache clear -d stripe.com   # re-run discovery next time
```

---

## Development setup

```bash
# Install dev dependencies
uv sync --all-extras --dev

# Run tests
uv run pytest tests/unit -v

# Run with coverage
uv run pytest tests/unit --cov=coldreach --cov-report=term-missing

# Lint + type check
uv run ruff check coldreach tests
uv run mypy coldreach

# Install pre-commit hooks
uv run pre-commit install
```

---

## Next steps

- [CLI Reference](cli-reference.md) — all commands and flags
- [How It Works](how-it-works.md) — verification pipeline and scoring
- [Discovery Sources](sources.md) — what each source finds and when to use it
- [Configuration](configuration.md) — full `.env` reference
