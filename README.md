# ColdReach

**Open-source email finder and lead discovery — the free alternative to Hunter.io and Apollo.io.**

[![CI](https://github.com/dhruvmojila/coldreach/actions/workflows/ci.yml/badge.svg)](https://github.com/dhruvmojila/coldreach/actions)
[![PyPI](https://img.shields.io/pypi/v/coldreach)](https://pypi.org/project/coldreach/)
[![Python](https://img.shields.io/pypi/pyversions/coldreach)](https://pypi.org/project/coldreach/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Coverage](https://codecov.io/gh/dhruvmojila/coldreach/branch/main/graph/badge.svg)](https://codecov.io/gh/dhruvmojila/coldreach)

---

```
$ coldreach verify patrick@stripe.com

  ✓  patrick@stripe.com  confidence 45/100

  Check        Status   Detail
  syntax       pass     Valid RFC 5322 syntax
  disposable   pass     Not a disposable email domain
  dns          pass     Found 5 MX record(s)

  MX: aspmx.l.google.com, alt1.aspmx.l.google.com (+3 more)
```

---

## Why ColdReach?

|                     | Hunter.io     | Apollo.io     | **ColdReach**          |
| ------------------- | ------------- | ------------- | ---------------------- |
| Cost                | $34–$399/mo   | $49–$149/mo   | **Free forever**       |
| Self-hosted         | No            | No            | **Yes**                |
| Source code         | Closed        | Closed        | **Open source**        |
| Rate limits         | 25k/mo        | 10k/mo        | **None (local)**       |
| API keys required   | Yes           | Yes           | **No** (Groq optional) |
| Privacy             | Their servers | Their servers | **Your machine only**  |
| Job board extension | Paid          | Paid          | **Free**               |
| TUI interface       | No            | No            | **Yes**                |

**ColdReach is honest about accuracy**: we'll find fewer emails than paid tools that have years of indexed data. But it's free, private, and you own everything.

---

## Install

```bash
pip install coldreach
```

For the full stack (web crawling, SMTP verification, OSINT):

```bash
docker compose up -d
pip install coldreach
```

---

## Quick Start

```bash
# Verify a single email address
coldreach verify john@acme.com

# Verify and get JSON output (pipe-friendly)
coldreach verify john@acme.com --json

# Find emails for a domain  (Phase 2 — coming soon)
coldreach find --domain acme.com

# Find email for a specific person (Phase 2)
coldreach find --domain acme.com --name "John Smith"
```

---

## How It Works

ColdReach combines multiple open-source OSINT tools and data sources, running them in parallel and scoring results by confidence.

### Verification Pipeline (Phase 1 — available now)

```
Email input
    │
    ▼
① Syntax check        — RFC 5322 validation (cpu-only, instant)
    │ fail → stop
    ▼
② Disposable check    — 500+ known throwaway domains (cpu-only, instant)
    │ fail → stop
    ▼
③ DNS / MX check      — async dnspython, catch-all detection
    │
    ▼
④ Reacher SMTP        — Rust microservice, handles Gmail/Outlook quirks (Phase 2)
    │
    ▼
⑤ Holehe platforms    — checks 120+ platforms, works on catch-all domains (Phase 2)
    │
    ▼
⑥ Source scoring      — confidence score from all discovery signals (Phase 2)
    │
    ▼
Ranked result [0–100 confidence]
```

### Discovery Sources (Phase 2)

| Source                     | What it finds                   | Free? |
| -------------------------- | ------------------------------- | ----- |
| Website crawler (Crawl4AI) | Emails on /contact /team /about | ✓     |
| Firecrawl (self-hosted)    | JS/React sites                  | ✓     |
| theHarvester               | OSINT: certs, Bing, Google, PGP | ✓     |
| SpiderFoot (self-hosted)   | WHOIS, DNS, social graph        | ✓     |
| GitHub commit mining       | Dev team emails                 | ✓     |
| Reddit JSON API            | Person/company mentions         | ✓     |
| WHOIS lookup               | Domain registrant               | ✓     |
| SearXNG (self-hosted)      | Web search (40+ engines)        | ✓     |
| Common Crawl CDX           | 300B+ page index                | ✓     |

---

## Docker Services

All backend services run via Docker Compose. The `coldreach` Python package is the CLI/TUI client.

```bash
# Start everything
docker compose up -d

# Or start only what you need
docker compose up reacher redis -d    # SMTP verification + cache
docker compose up searxng -d          # Metasearch
docker compose up spiderfoot -d       # Deep OSINT
```

| Service      | Port | Purpose                                           |
| ------------ | ---- | ------------------------------------------------- |
| `postgres`   | 5432 | Persistent storage (optional — SQLite is default) |
| `redis`      | 6379 | Result cache (7-day TTL)                          |
| `searxng`    | 8080 | Metasearch (40+ engines)                          |
| `reacher`    | 8083 | SMTP email verification (Rust)                    |
| `spiderfoot` | 5001 | Deep OSINT                                        |
| `firecrawl`  | 3002 | JS-heavy site crawling                            |

---

## Configuration

```bash
cp .env.example .env
```

All variables are optional. ColdReach works out of the box with SQLite and no API keys.

```env
# Only key you might want (free tier at console.groq.com)
COLDREACH_GROQ_API_KEY=gsk_xxx   # unlocks LLM email personalization
```

Everything else has sensible defaults. See [.env.example](.env.example) for full reference.

---

## Project Status

| Phase       | Status         | Description                                                    |
| ----------- | -------------- | -------------------------------------------------------------- |
| **Phase 1** | ✅ In progress | Scaffold + email verification (syntax, disposable, DNS)        |
| Phase 2     | Planned        | Multi-source discovery (website, GitHub, Reddit, OSINT)        |
| Phase 3     | Planned        | Chrome extension (job board → find hiring manager contact)     |
| Phase 4     | Planned        | Cold email outreach (templates, LLM personalization, Listmonk) |
| Phase 5     | Planned        | BYOK (Hunter.io, Apollo.io, Clearbit)                          |

---

## Development

```bash
# Install dev dependencies (uv recommended)
pip install uv
uv sync --all-extras --dev

# Run tests
uv run pytest tests/unit -v

# Run with coverage
uv run pytest tests/unit --cov=coldreach --cov-report=term-missing

# Lint + format
uv run ruff check coldreach tests
uv run ruff format coldreach tests

# Type check
uv run mypy coldreach

# Install pre-commit hooks
uv run pre-commit install
```

---

## Accuracy Expectations

ColdReach is **honest** about what it can and cannot do:

- **Phase 1** (this release): Email _verification_ only — tells you if an email is likely valid
- **Phase 2** (coming): Email _discovery_ — finding emails via OSINT and crawling
- **Expected accuracy**: 50–65% for cold domains (vs 85–90% for Hunter.io)
- **Why lower?** Hunter.io has 100M+ indexed emails from years of crawling. We start at 0.
- **Catch-all domains** (Gmail Workspace, Office 365): SMTP verification is unreliable. We use Holehe platform checks instead.

---

## Legal Notice

ColdReach is a research and outreach tool. You are responsible for complying with applicable laws:

- **GDPR (EU)**: Generating emails for EU targets requires a lawful basis
- **CAN-SPAM (US)**: All commercial emails must include unsubscribe + physical address
- **LinkedIn ToS**: ColdReach does not directly scrape LinkedIn
- **Responsible use**: This tool is for legitimate outreach, not spam

---

## Contributing

Contributions welcome! The most valuable contributions are:

1. **New job board parsers** (Phase 3 Chrome extension)
2. **New data sources** — implement `BaseSource` protocol
3. **Disposable domain additions** — add to `coldreach/data/disposable_domains.txt`
4. **Bug reports** — open an issue with the email/domain and error

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide.

---

## License

MIT — see [LICENSE](LICENSE).
