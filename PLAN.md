# ColdReach — Open Source Lead Discovery & Email Finder

> A Python pip library + TUI/CLI + Chrome extension for finding professional contact emails.
> The open-source alternative to Hunter.io and Apollo.io.
> Install locally. Run free. No rate limits. Docker Compose for all backend services.
> Only external key required: Groq API (optional, for LLM personalization — has a generous free tier).

---

## BRUTAL HONEST CRITIQUE FIRST

Before anything else — here is what will kill this project if you ignore it.

### Critical Problems

**1. SMTP Verification is Mostly Broken for B2B**
The core promise of "verify if email exists" fails against the 2 biggest email providers:
- **Google Workspace** (40%+ of B2B companies): Returns 250 OK for EVERYTHING — it's catch-all by default.
- **Microsoft 365 / Outlook** (40%+ of enterprise): Same. They stopped responding honestly to RCPT TO probes years ago.
- Result: SMTP-based verification is reliable for maybe 20-30% of actual business email domains.
- Workaround: Multi-signal scoring (sources, recency, Holehe platform check, pattern confidence) — not a silver bullet.
- This is the same problem Hunter.io has. Their "verified" badge is often meaningless for corporate domains.

**2. LinkedIn Has All the Data — And You Cannot Touch It**
- LinkedIn is where every professional lists their current job title, company, and contact info.
- Scraping it violates ToS, can result in lawsuits (LinkedIn has won in court against scrapers).
- The EU GDPR makes it even worse — scraping EU profiles is a GDPR violation.
- Apollo and Hunter have years of indexed data from when LinkedIn was more open. You don't.
- You will have to build without this. That means lower accuracy for job title / person matching.

**3. Data Goes Stale Immediately**
- 30% of B2B email addresses become invalid each year (people change jobs, companies pivot).
- Hunter/Apollo invest heavily in continuous re-crawling and refresh cycles.
- A one-time scrape is useless in 6 months.
- You need an update strategy baked in from day 1 — cache TTL must be short (7 days max).

**4. "Just pip install it" is a Lie**
For this tool to work at any useful depth, users need:
- Docker + Docker Compose (for SearXNG, Firecrawl, SpiderFoot, Reacher, Redis)
- A headless browser (Playwright/Chromium — 300MB)
- This is not "npm install streamlit". This is a DevOps project.
- Honest answer: `docker compose up` is the real install. `pip install coldreach` is just the CLI client.
- You must be honest about setup complexity in docs.

**5. SearXNG Rate Limiting is Real and Painful**
- SearXNG is just a proxy. When you hammer it, underlying engines (Google, Brave, Bing) block its IP.
- On a residential/cloud IP, Google starts dropping queries after 20–30 searches in an hour.
- Mitigation: engine rotation, request throttling, DuckDuckGo Lite fallback, multiple SearXNG instances.
- Do NOT treat SearXNG as unlimited in practice. Budget 1 query per 5–10 seconds per engine.

**6. Chrome Extension is a Separate Full Product**
The Chrome extension is NOT a small feature to bolt on. It requires:
- Chrome Manifest V3 (different from V2, actively maintained)
- A local API server for the extension to call (FastAPI, coldreach serve)
- DOM parsers for each job board (LinkedIn Jobs, Indeed, Greenhouse, Lever, etc.)
- Each job board changes its DOM regularly — constant maintenance
- This is 4-6 weeks of work alone, separate from the library
- Scope it as Phase 3+ minimum

**7. Legal Risk for Users**
- GDPR (EU): Generating email addresses by combining public names + domains is illegal without consent.
- CAN-SPAM (US): Must include unsubscribe mechanism, physical address, accurate headers.
- If your tool makes it easy to spam, you will be held partly responsible by community.
- You MUST build opt-out checking into the outreach layer, or you will be reported and banned from GitHub.

**8. Open Source Does Not Mean Users Trust It**
- Privacy-conscious decision makers will not feed company names into a random OSS tool.
- You need: audit-able code, no telemetry, explicit local-only mode, clear data policy.
- Enterprise users (who have money) are the most paranoid.

**9. You Are Not Competing With Hunter.io — You Are Serving a Different Market**
- Hunter/Apollo serve enterprise sales teams with $500/mo budgets.
- You should serve: students, indie founders, job seekers, bootstrapped startups.
- This is a smaller but underserved market. Own it. Don't claim you'll replace Apollo — you won't.
- The job seeker Chrome extension use case is your strongest differentiator. Lean into it hard.

**10. Accuracy Will Be Lower Than Paid Tools**
- Hunter.io has a database of 100M+ indexed emails. You start at 0.
- Your accuracy early on will be 40-60% at best. Be transparent about confidence scoring.
- Email guessing + multi-signal verification is better than nothing but worse than paid tools.

**11. Common Crawl is Huge but Hard**
- Common Crawl is 300TB of data. Mining it for emails is a MapReduce/Spark job.
- It is NOT suitable for real-time queries in a CLI tool.
- Use it to build an offline index (HuggingFace Dataset), not for on-demand search.

---

## WHAT IS ACTUALLY FEASIBLE & VALUABLE

Despite the critique above, this IS worth building. Here is what genuinely works:

- Company website crawling (contact/team/about pages) — reliable, underused
- GitHub commit email mining — surprisingly effective for tech company founders/devs
- WHOIS data — good for registrant contact info
- Email pattern generation + multi-signal verification (SMTP + Holehe + Reacher)
- theHarvester + SpiderFoot — already do multi-source OSINT well
- Reddit JSON API — completely free, no auth, underused for company/person mentions
- Job board Chrome extension — clear user value, no legal grey area
- LLM email personalization with Groq free tier (only optional key)
- SQLite local caching — no re-querying same domain twice

---

## TOOL NAME: `coldreach`

**Primary install:** `docker compose up` (spins up all backend services)
**CLI client:** `pip install coldreach`

**TUI (default):** `coldreach` — launches full Terminal UI (Textual-based)
**CLI (headless/scripting):** `coldreach --no-tui find --domain acme.com`

---

## UI DECISION: TUI, NOT STREAMLIT

### Why TUI with Textual, not Streamlit

| Criteria | Streamlit | TUI (Textual) | Winner |
|----------|-----------|----------------|--------|
| Feels like a real tool | No (browser) | Yes (terminal-native) | TUI |
| Works in SSH / remote env | No | Yes | TUI |
| Works offline | No (needs browser) | Yes | TUI |
| For dev/power users | Weak | Strong | TUI |
| Startup speed | Slow (browser launch) | Instant | TUI |
| Works with CLI piping | No | Yes | TUI |
| pip install complexity | Medium | Light | TUI |
| Looks impressive in demos | Medium | Very (modern TUI) | TUI |

**Textual** (by Textualize — makers of Rich):
- 20k+ stars on GitHub
- Async-native, CSS-like styling
- Tables, forms, progress bars, panels — everything you need
- Runs in any terminal: iTerm, Windows Terminal, VS Code terminal

**Streamlit** demoted to optional: `coldreach dashboard` can launch a Streamlit web UI for non-technical users who want a browser view. But TUI is the primary experience.

### TUI Layout

```
┌─ ColdReach ──────────────────────────────────────────────────────────┐
│ [Find]  [Verify]  [Enrich]  [Outreach]  [Cache]  [Settings]  [Help] │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Company / Domain: [stripe.com________________]   [Find Emails]      │
│  Person Name:      [John Smith________________]   (optional)         │
│                                                                       │
│  Sources: [x] Website  [x] theHarvester  [x] GitHub  [x] WHOIS      │
│           [x] Reddit   [x] SpiderFoot   [ ] CommonCrawl              │
│                                                                       │
├──── Results ─────────────────────────────────────────────────────────┤
│  Email                          Score  Source              Status    │
│  ─────────────────────────────  ─────  ──────────────────  ───────── │
│  patrick@stripe.com             87     website/team        verified  │
│  john@stripe.com                62     theHarvester/bing   unverif   │
│  legal@stripe.com               91     website/contact     verified  │
│                                                                       │
│  [Copy]  [Draft Email]  [Verify]  [Add to Sequence]  [Export CSV]   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## DOCKER COMPOSE ARCHITECTURE

This is the real "install". All backend services run via Docker Compose.
The `coldreach` Python package is the CLI/TUI client that talks to these services.

```yaml
# docker-compose.yml
services:

  searxng:            # Metasearch engine (rate-limited by upstream engines)
    image: searxng/searxng
    ports: ["8080:8080"]
    volumes: ["./config/searxng:/etc/searxng"]

  firecrawl:          # JS-heavy site crawling (self-hosted)
    image: ghcr.io/mendableai/firecrawl
    ports: ["3002:3002"]
    depends_on: [redis]

  spiderfoot:         # Deep OSINT: WHOIS, DNS, social, data breaches
    image: smicallef/spiderfoot
    ports: ["5001:5001"]

  reacher:            # SMTP email verification microservice (Rust, very fast)
    image: reacherhq/backend
    ports: ["8083:8083"]

  redis:              # Cache layer (shared between firecrawl + coldreach)
    image: redis:7-alpine
    ports: ["6379:6379"]

  postgres:           # Persistent storage: leads, contacts, emails, sequences
    image: postgres:16
    environment:
      POSTGRES_DB: coldreach
      POSTGRES_USER: coldreach
      POSTGRES_PASSWORD: coldreach
    ports: ["5432:5432"]
    volumes: ["coldreach_pg_data:/var/lib/postgresql/data"]

  coldreach-api:      # FastAPI server (Chrome extension + TUI backend)
    build: .
    ports: ["8765:8765"]
    depends_on: [postgres, redis, searxng, reacher]
    env_file: .env

volumes:
  coldreach_pg_data:
```

### Service Map

```
coldreach TUI / CLI
        │
        ▼
coldreach-api (FastAPI :8765)
        │
        ├── SearXNG (:8080)         — metasearch (rate-limit aware)
        │     └── Google/Brave/Bing/DDG/Qwant (underlying engines)
        │
        ├── Firecrawl (:3002)       — JS-heavy site crawling
        │     └── Redis (:6379)     — Firecrawl's internal cache
        │
        ├── SpiderFoot (:5001)      — deep OSINT per domain
        │     └── REST API          — query via /api/scanresults
        │
        ├── Reacher (:8083)         — SMTP email verification
        │     └── Handles: catch-all detection, Hotmail/Yahoo quirks
        │
        ├── PostgreSQL (:5432)      — all persistent data
        │
        ├── Redis (:6379)           — coldreach result cache (TTL 7 days)
        │
        └── External (open, no auth required):
              ├── theHarvester      — subprocess (runs locally)
              ├── GitHub REST API   — commit email mining
              ├── WHOIS             — python-whois library
              ├── Reddit JSON API   — no auth, 100 req/10min
              └── Common Crawl CDX  — HTTP index queries
```

---

## ARCHITECTURE — Python Package

```
coldreach/                        # Python package
├── __init__.py
├── cli.py                        # Click CLI (--no-tui mode)
├── tui/
│   ├── app.py                    # Textual App entrypoint
│   ├── screens/
│   │   ├── find.py               # Find emails screen
│   │   ├── verify.py             # Verify email screen
│   │   ├── outreach.py           # Draft/send email screen
│   │   └── settings.py           # Config screen
│   └── widgets/
│       ├── results_table.py      # Results datatable widget
│       └── source_selector.py    # Source toggle checkboxes
├── api.py                        # FastAPI server (Chrome extension + TUI backend)
├── dashboard.py                  # Optional Streamlit web UI
├── core/
│   ├── finder.py                 # Main find_emails() orchestrator
│   ├── domain_resolver.py        # Company name → domain
│   └── scorer.py                 # Confidence scoring engine
├── sources/
│   ├── base.py                   # BaseSource ABC
│   ├── web_crawler.py            # Crawl4AI + Firecrawl contact page crawler
│   ├── search_engine.py          # SearXNG queries (with rate-limit fallback chain)
│   ├── github.py                 # GitHub commit email mining
│   ├── whois_source.py           # WHOIS registrant data
│   ├── harvester.py              # theHarvester subprocess wrapper
│   ├── spiderfoot.py             # SpiderFoot REST API client
│   ├── reddit.py                 # Reddit JSON API (no auth)
│   └── common_crawl.py           # Common Crawl CDX API
├── verify/
│   ├── pipeline.py               # Orchestrates all verification steps
│   ├── syntax.py                 # RFC 5322 syntax
│   ├── disposable.py             # Throwaway domain blocklist (2000+ domains)
│   ├── dns_check.py              # MX records + domain existence
│   ├── catchall.py               # Catch-all detection (test with fake address)
│   ├── reacher.py                # Reacher microservice client (SMTP verification)
│   └── holehe.py                 # Holehe: check email on 120+ platforms
├── generate/
│   ├── patterns.py               # 12 email format generators
│   └── learner.py                # Infer domain's email format from found emails
├── enrich/
│   ├── company.py                # Clearbit Autocomplete (free, no auth) + fallbacks
│   └── person.py                 # LinkedIn via search engine + GitHub profile
├── outreach/
│   ├── templates.py              # Cold email template engine with placeholders
│   ├── personalize.py            # Groq LLM personalization (optional key)
│   └── sender.py                 # Listmonk / SMTP send
├── storage/
│   ├── cache.py                  # Redis + SQLite cache
│   └── models.py                 # SQLAlchemy models (PostgreSQL)
└── config.py                     # pydantic-settings (.env config)

chrome-extension/                 # Chrome Extension (Phase 3)
├── manifest.json                 # V3 manifest
├── src/
│   ├── popup/                    # React popup UI
│   ├── background/               # Service worker
│   └── content/                  # Per-job-board content scripts
│       ├── greenhouse.js
│       ├── lever.js
│       ├── indeed.js
│       └── workable.js
└── build/

docker-compose.yml
docker-compose.dev.yml
.env.example
docs/                             # mkdocs-material site
pyproject.toml                    # Poetry config
```

---

## CORE ALGORITHMS

### Finding Emails for a Domain (Priority Order)

```
0. Check Redis cache (TTL 7 days) — return immediately if hit

1. Crawl company website (parallel):
   a. Crawl4AI: GET homepage → find /contact /team /about /people /staff links
   b. Firecrawl (if JS-heavy — detect via content-type/JS framework heuristic)
   c. Extract all email patterns via regex
   d. Parse mailto: links
   e. Handle obfuscation: [at] → @, "email protected", JS-split patterns

2. theHarvester scan:
   a. Sources: google, bing, duckduckgo, certspotter, crtsh, pgp, hackertarget
   b. Parse stdout for email patterns

3. SearXNG queries (rate-limit aware — max 1 query/5s per engine):
   a. Query 1: "@domain.com" site:domain.com
   b. Query 2: "domain.com" email contact
   c. Rotate engines: Brave → DDG → Qwant → Yahoo (avoid Google for bulk)
   d. Fallback chain: SearXNG → DuckDuckGo Lite HTML → Brave Search API

4. Reddit JSON API (no auth required):
   a. GET https://www.reddit.com/search.json?q="domain.com"+email&sort=new
   b. GET https://www.reddit.com/search.json?q="company name"+contact
   c. Parse post bodies and comments for email patterns
   d. Rate limit: 1 req/1s, User-Agent: "coldreach/0.1 (contact finder)"

5. GitHub mining:
   a. Search GitHub API: org:company-slug
   b. Fetch recent commits from main repos → extract author.email
   c. Also: search "company name" in GitHub users → profile emails
   d. Rate limit: 5000/hr authenticated, 60/hr unauthenticated

6. WHOIS lookup:
   a. python-whois → registrant email, admin email, tech email
   b. Reverse WHOIS if registrant name known

7. SpiderFoot (for high-value leads):
   a. POST /api/newscan → scan domain for OSINT intel
   b. Poll GET /api/scanresults → parse EMAIL_ADDR type results
   c. Also returns: social profiles, subdomains, DNS data

8. Common Crawl CDX API (async, background):
   a. Query CDX index: http://index.commoncrawl.cc/CC-MAIN-*/cdx?url=domain.com/*
   b. Fetch top WAT files → extract email hints
   c. Run as background job, results appended when available

9. Pattern Generation (if person name known):
   a. Generate 12 format variants
   b. Verify each via full verification pipeline
   c. Only generate if ≥1 real email found at domain (to learn format)

10. Score all found/generated emails → return ranked list
    Cache result in Redis (TTL 7 days) + PostgreSQL (permanent record)
```

### Email Verification Pipeline (Layered, Stop on High Confidence)

```
For each candidate email:

  Layer 1 — Fast Discard (no network)
    1a. Syntax check (RFC 5322) → reject malformed
    1b. Disposable domain check (2000+ domains list) → reject burner emails
    → If fail: score = 0, discard

  Layer 2 — DNS (fast network)
    2a. MX record lookup → does domain have mail server?
    2b. A/AAAA record → does domain exist at all?
    → If fail: score = 0, discard

  Layer 3 — Catch-All Detection
    3a. Send SMTP RCPT TO probe with random_xyz_abc@domain.com
    3b. If 250 OK → catch-all detected → flag domain as catch-all
    3c. If catch-all: skip SMTP for all emails at this domain, mark "unverifiable"

  Layer 4 — Reacher SMTP Verification (if not catch-all)
    4a. POST http://localhost:8083/v0/check_email {"to_email": "..."}
    4b. Reacher handles: Hotmail quirks, Yahoo quirks, proper TLS, timeout
    4c. Parse response: is_reachable = "safe" | "risky" | "invalid" | "unknown"
    → Reacher is MUCH better than raw smtplib — use it as primary SMTP tool

  Layer 5 — Holehe Platform Check
    5a. holehe.check(email) → checks 120+ platforms (LinkedIn, Slack, GitHub, etc.)
    5b. If registered on 3+ platforms → email is live, person is active
    5c. This works even for catch-all domains — platform registration is independent of SMTP
    → Most valuable check for catch-all domains where SMTP is useless

  Layer 6 — Source Scoring
    +35 pts  found directly on company website (/team /contact /about)
    +25 pts  found via theHarvester (multi-source corroboration)
    +20 pts  found via SpiderFoot
    +20 pts  Reacher returned is_reachable = "safe"
    +15 pts  Holehe: registered on 3+ platforms
    +10 pts  found in Reddit post/comment
    +10 pts  pattern matches known format for this domain
    +10 pts  found in GitHub commit
    + 5 pts  WHOIS registrant match
    - 5 pts  only pattern-generated (no source confirmation)
    -15 pts  catch-all domain (SMTP unverifiable)
    -20 pts  Reacher returned is_reachable = "risky"

  Final score: 0–100
  Cache result: Redis TTL=7 days, PostgreSQL permanent
```

### SearXNG Rate Limit Fallback Chain

```
Query attempt:
  1. SearXNG (primary) — if response time < 5s and results > 0 → use it
  2. If SearXNG returns 0 results or timeout:
     → Fallback 1: DuckDuckGo Lite (https://lite.duckduckgo.com/lite?q=...) — no JS, parseable HTML
  3. If DDG Lite also blocked:
     → Fallback 2: Brave Search API (free, 2000/month at api.search.brave.com)
  4. If all fail:
     → Log warning: "Search sources temporarily rate-limited. Results may be incomplete."
     → Continue with other non-search sources (crawler, GitHub, WHOIS, Reddit)

Rate limit strategy:
  - Min 5 seconds between SearXNG queries
  - Rotate SearXNG engines: never use Google directly; use Brave/Qwant/DDG
  - Respect Retry-After headers
  - Redis: cache search results per query string, TTL 24 hours
```

### Email Pattern Generator (12 Formats)

Given name "John Smith" + domain "acme.com":
```
john@acme.com
j.smith@acme.com
jsmith@acme.com
john.smith@acme.com
johnsmith@acme.com
smith.john@acme.com
smithj@acme.com
smith@acme.com
johns@acme.com
john_smith@acme.com
j_smith@acme.com
jsmith1@acme.com  (collision variant)
```

Pattern priority determined by `generate/learner.py`:
- If we already found emails at this domain, analyze their format first
- Generate only the format(s) that match the domain's known pattern
- Avoids spamming 12 variants when the company clearly uses first.last@ format

### Domain Finder (Company Name → Domain)

```
1. Clearbit Autocomplete API (free, no auth):
   GET https://autocomplete.clearbit.com/v1/companies/suggest?query=acme+corp
   → Returns domain + logo + name. Fast, accurate, no key.

2. SearXNG query: "acme corp" official website site:acme.com
   → Parse for most probable domain from top results

3. DuckDuckGo Instant Answer API (free):
   GET https://api.duckduckgo.com/?q=acme+corp&format=json
   → Check AbstractURL field

4. Validate result:
   → HTTP 200 response from domain
   → HTML contains company name or related keywords

5. Cache in Redis + PostgreSQL
```

---

## TECH STACK

| Component | Tool | Why |
|-----------|------|-----|
| TUI (primary UI) | `Textual` (Textualize) | Terminal-native, async, CSS styling, 20k stars |
| CLI (scripting) | `click` | Standard, pipes well |
| HTTP | `httpx` (async) | Async, connection pooling |
| Web crawling | `Crawl4AI` | Primary: fast, async, LLM-ready markdown |
| JS site crawling | `Firecrawl` (self-hosted Docker) | For React/SPA sites |
| DNS | `dnspython` | MX/A/TXT lookups |
| SMTP verification | `Reacher` (Docker microservice) | Purpose-built Rust SMTP verifier, handles edge cases |
| Email platform check | `Holehe` | 120+ platform checks, works on catch-all domains |
| OSINT (multi-source) | `theHarvester` (subprocess) | 40+ sources, proven tool |
| OSINT (deep) | `SpiderFoot` (Docker) | REST API, WHOIS/DNS/social graph |
| Domain lookup | `python-whois` | WHOIS data |
| Search | `SearXNG` (Docker) | Primary; DuckDuckGo Lite + Brave as fallbacks |
| Reddit | Reddit JSON API | Free, no auth, 100 req/10min |
| GitHub | GitHub REST API | Commit emails, org members |
| Local DB | `PostgreSQL` (Docker) | Permanent storage |
| Cache | `Redis` (Docker) | 7-day result TTL, search cache |
| ORM | `SQLAlchemy` async | Type-safe DB access |
| API server | `FastAPI` + `uvicorn` | Chrome extension + TUI backend |
| Web UI (opt) | `Streamlit` | Optional browser dashboard |
| LLM (opt) | `Groq API` (BYOK — only key needed) | Free tier, Llama 3.1 70B, email personalization |
| Email send | `Listmonk` (self-hosted) or SMTP | Sequences, tracking |
| Config | `pydantic-settings` + `.env` | Type-safe config |
| Packaging | `Poetry` + `pyproject.toml` | Modern Python packaging |

---

## DATA SOURCES — RANKED BY RELIABILITY

| Source | Type | Accuracy | Rate Limit | Legal | Notes |
|--------|------|----------|------------|-------|-------|
| Company website /contact | Crawl | High | None | Clear | Best signal |
| Company website /team | Crawl | High | None | Clear | Best signal |
| theHarvester | OSINT | Medium-High | Varies | Clear | Multi-source aggregator |
| SpiderFoot | OSINT | Medium-High | None (local) | Clear | Deeper than theHarvester |
| GitHub commits | API | High (tech cos) | 5000/hr (auth) | Clear | Best for tech companies |
| WHOIS registrant | Library | Medium | None | Clear | Often redacted post-GDPR |
| Reddit JSON API | API | Low-Medium | 100 req/10min | Clear | Underused, surprisingly useful |
| Common Crawl CDX | API | Medium | None | Clear | Months old, offline index |
| Email pattern + Reacher | Generated | Low-Medium | SMTP limits | Clear | Needs name + domain |
| Holehe | Platform check | Medium | Varies | Clear | Platform registration ≠ work email |
| SearXNG | Metasearch | Medium | Rate-limited | Clear | Fallback to DDG Lite / Brave |
| LinkedIn via search | Indirect | Medium | Varies | Grey | Name extraction only |
| Direct LinkedIn scrape | Scrape | High | Instant ban | Illegal | DO NOT DO |

---

## GROQ API — ONLY OPTIONAL KEY

All features work without any API keys. Groq is the single optional key that unlocks LLM capabilities:

```env
# .env — only key you might want
COLDREACH_GROQ_KEY=gsk_xxx   # optional — unlocks email personalization
```

What Groq unlocks:
- Personalized cold email drafting (company context → Groq → email draft)
- Subject line variants (A/B suggestions)
- Company summary from crawled page content
- Email template filling with contextual language

Groq free tier: 14,400 tokens/minute on llama-3.1-70b-versatile — plenty for this use case.

**BYOK for paid APIs (Hunter, Apollo, Clearbit, etc.) is deferred to a future phase.**
They add accuracy but ship complexity. Build with 100% free tools first. Add BYOK after v1.0 is solid.

---

## PHASE PLAN

### Phase 1 — Core Engine (Weeks 1–3)
**Goal: End-to-end working pipeline. `coldreach find --domain acme.com` returns ranked emails.**

**Infrastructure:**
- [ ] `docker-compose.yml` with: SearXNG, Reacher, Redis, PostgreSQL
- [ ] `.env.example` + `config.py` (pydantic-settings)
- [ ] PostgreSQL schema + SQLAlchemy models
- [ ] Redis cache layer (TTL 7 days)

**Core Discovery:**
- [ ] Company website crawler (Crawl4AI — /contact /team /about pages)
- [ ] Email regex extractor (handles obfuscated emails too)
- [ ] theHarvester subprocess wrapper + output parser
- [ ] GitHub commit email miner (public repos, no auth first)
- [ ] WHOIS registrant email extractor
- [ ] Reddit JSON API source module

**Verification:**
- [ ] Syntax check (RFC 5322)
- [ ] Disposable domain blocklist (2000+ domains)
- [ ] DNS MX record check (dnspython)
- [ ] Catch-all domain detection
- [ ] Reacher microservice client (SMTP verification)
- [ ] Holehe platform check integration

**Scoring & Output:**
- [ ] Confidence scoring engine (source-based points)
- [ ] Email pattern generator (12 formats)
- [ ] Pattern learner (infer domain format from known emails)

**CLI:**
- [ ] `coldreach find --domain acme.com`
- [ ] `coldreach find --company "Stripe" --name "John Smith"`
- [ ] `coldreach verify john@stripe.com`
- [ ] `coldreach --no-tui` headless mode (JSON output for scripting)
- [ ] PyPI publish pipeline (GitHub Actions)

**Deliverable:** `pip install coldreach` + `docker compose up` → working email finder

---

### Phase 2 — TUI + Enhanced Sources (Weeks 4–5)
**Goal: Full TUI, better accuracy, more sources**

**TUI (Textual):**
- [ ] `coldreach` launches Textual app
- [ ] Find screen with source toggles
- [ ] Results table (sortable, copyable)
- [ ] Verify email screen
- [ ] Settings screen (config editor)
- [ ] Cache browser (view/clear cached results)

**Enhanced Sources:**
- [ ] Firecrawl Docker service + integration (JS-heavy sites)
- [ ] SpiderFoot Docker service + REST API client
- [ ] SearXNG integration with rate-limit fallback chain
- [ ] DuckDuckGo Lite fallback scraper
- [ ] Brave Search API fallback (free tier)
- [ ] Common Crawl CDX API (async background, results appended)
- [ ] Company domain resolver (Clearbit Autocomplete → SearXNG → DDG)
- [ ] `coldreach find --company "Stripe"` (name → domain → emails)

**Storage:**
- [ ] Export results: CSV, JSON
- [ ] `coldreach cache list` — show all cached domains
- [ ] `coldreach cache clear --domain stripe.com`

**Deliverable:** `coldreach` → full TUI, multiple sources, solid accuracy for tech companies

---

### Phase 3 — Chrome Extension (Weeks 6–8)
**Goal: One-click email finding from any job posting**

- [ ] FastAPI server: `coldreach serve` (starts :8765 for extension)
- [ ] Chrome Extension (Manifest V3, React popup)
- [ ] Greenhouse ATS DOM parser
- [ ] Lever ATS DOM parser
- [ ] Indeed DOM parser
- [ ] Workable DOM parser
- [ ] LinkedIn Jobs: indirect (search engine lookup, no direct scrape)
- [ ] Email template engine with placeholders
- [ ] Groq personalization in extension popup (BYOK, optional)
- [ ] Chrome Web Store publish

**Deliverable:** Open job posting → 10 seconds → hiring manager email in clipboard

---

### Phase 4 — Outreach Layer (Weeks 9–10)
**Goal: Cold email end-to-end, from find to send**

- [ ] Cold email template library (job application, B2B sales, partnership)
- [ ] LLM personalization: Crawl4AI fetches company context → Groq drafts email
- [ ] Listmonk integration: send, sequence, track opens/clicks
- [ ] IMAP reply detection (pause sequence on reply)
- [ ] Opt-out list management (legally required — check before every send)
- [ ] Follow-up sequence: Day 3, Day 7, Day 14 (configurable)
- [ ] A/B subject line testing
- [ ] TUI outreach screen: write → review → send

---

### Phase 5 — BYOK & Community (Ongoing)
**Goal: Higher accuracy for users who want it; community contributions**

- [ ] Hunter.io BYOK integration (25/month free fallback)
- [ ] Apollo.io BYOK integration (50/month free)
- [ ] Clearbit enrichment BYOK
- [ ] Pre-built email index from Common Crawl → HuggingFace Dataset
- [ ] Plugin API: `BaseSource` ABC allows community-contributed sources
- [ ] Contribution guide: adding job board parsers
- [ ] Documentation site (mkdocs-material)
- [ ] Discord community
- [ ] Accuracy benchmarks vs Hunter.io free tier (published publicly)

---

## KEY DIFFERENTIATORS vs Hunter.io / Apollo.io

| Feature | Hunter.io | Apollo.io | ColdReach |
|---------|-----------|-----------|-----------|
| Cost | $34–$399/mo | $49–$149/mo | Free forever |
| Self-hosted | No | No | Yes (Docker) |
| Source code | Closed | Closed | Open source |
| Rate limits | 25–50k/mo | 50–10k/mo | None (local) |
| Data freshness | Real-time DB | Real-time DB | On-demand crawl |
| Accuracy (honest) | 85-90% | 80-85% | 50-70% |
| API key required | Yes | Yes | No (Groq optional) |
| Privacy | Their servers | Their servers | Your machine only |
| Chrome extension | Paid plan | Paid plan | Free, job boards |
| Job board focus | No | No | Yes — key differentiator |
| LLM personalization | No | No | Yes (Groq free tier) |
| TUI interface | No | No | Yes |
| Multi-source OSINT | No | No | Yes (theHarvester + SpiderFoot + Reddit) |
| Email sequences | No | Partial | Yes (Listmonk) |

---

## EXISTING TOOLS TO INTEGRATE (NOT REBUILD)

| Tool | Stars | Use Case | Integration Method |
|------|-------|----------|--------------------|
| [theHarvester](https://github.com/laramies/theHarvester) | 11k+ | Multi-source OSINT email mining | `subprocess` call |
| [Holehe](https://github.com/megadose/holehe) | 2.8k | Email → 120+ platform registrations | `import holehe` |
| [Reacher](https://github.com/reacherhq/check-if-email-exists) | 5k+ | SMTP email verification microservice | Docker + REST API |
| [SpiderFoot](https://github.com/smicallef/spiderfoot) | 12k+ | Deep OSINT: WHOIS/DNS/social graph | Docker + REST API |
| [CrossLinked](https://github.com/m8sec/CrossLinked) | 1k+ | LinkedIn name harvesting via search | `subprocess` call |
| [Crawl4AI](https://github.com/unclecode/crawl4ai) | 50k+ | Async contact page crawling | `import crawl4ai` |
| [Firecrawl](https://github.com/mendableai/firecrawl) | 70k+ | JS-heavy/SPA site crawling | Docker + REST API |
| [h8mail](https://github.com/khast3x/h8mail) | 5k | Email breach checking | `import h8mail` |
| [Textual](https://github.com/Textualize/textual) | 20k+ | Terminal UI framework | `import textual` |
| [python-whois](https://pypi.org/project/python-whois/) | — | WHOIS lookups | `pip install` |
| [dnspython](https://pypi.org/project/dnspython/) | — | MX/DNS checks | `pip install` |

---

## WHAT NOT TO BUILD

- **Your own web crawler** — Crawl4AI exists. Use it.
- **Your own SMTP verifier** — Reacher (Rust) is battle-tested. Use it via Docker.
- **Your own breach database** — h8mail does this. Use it.
- **Your own WHOIS parser** — python-whois exists. Use it.
- **Your own TUI from scratch** — Textual is 20k stars. Use it.
- **Common Crawl real-time index** — It's 300TB. Build an offline index separately.
- **Your own email RFC validator** — email-validator on PyPI handles RFC 5322.
- **Streamlit as primary UI** — Demoted to optional. TUI is primary.

---

## LEGAL COMPLIANCE (built in from day 1)

1. **Opt-out list**: Local PostgreSQL table. Check before every email operation.
2. **GDPR warning**: When EU domain detected (TLD + country heuristic), show warning.
3. **CAN-SPAM template**: Default templates include physical address and unsubscribe placeholders.
4. **Rate limiting**: Built-in delays between SMTP probes to avoid blacklisting your IP.
5. **Data transparency**: Every result shows source (where it was found). No magic confidence numbers.
6. **No telemetry**: Zero external calls except to user-configured APIs. Stated explicitly in README.
7. **Privacy mode**: `--no-cache` flag skips all SQLite/PostgreSQL writes. Leaves no trace.

---

## SUCCESS METRICS (Honest Targets)

| Metric | Month 1 | Month 3 | Month 6 |
|--------|---------|---------|---------|
| GitHub Stars | 50 | 500 | 2000 |
| PyPI Downloads/month | 100 | 1000 | 5000 |
| Email find accuracy | 40% | 55% | 65% |
| Verification accuracy | 60% | 65% | 70% |
| Job boards in extension | 2 | 4 | 6 |

---

## RECOMMENDED FIRST COMMIT

Start with this and nothing else:

```
$ coldreach --no-tui find --domain stripe.com

Scanning stripe.com ...
  [✓] Website crawled    — 2 emails found
  [✓] theHarvester       — 1 email found
  [✓] GitHub commits     — 3 emails found
  [✓] WHOIS              — 1 email found (redacted)
  [✓] Reddit             — 0 mentions
  [~] Reacher SMTP       — catch-all domain (unverifiable)
  [✓] Holehe check       — 2/3 emails active on platforms

Results for stripe.com (6 unique):
  patrick@stripe.com     [87/100]  website/team-page + Holehe:4 platforms
  legal@stripe.com       [91/100]  website/contact + Holehe:2 platforms
  john@stripe.com        [55/100]  theHarvester/bing + GitHub commit
  ...

Cached. Next lookup of stripe.com will be instant (7-day TTL).
```

Get this working. Everything else is features.

---

## COMMUNITY STRATEGY

- README: one-liner `docker compose up` + `pip install coldreach` at the top
- State accuracy honestly in README (don't lie — 50-65% for cold domains)
- GDPR/CAN-SPAM section visible in README (prevents GitHub abuse reports)
- Blog post: "We built a free Hunter.io alternative — here's how"
- HackerNews Show HN when v0.1.0 ships
- Contribution guide: adding job board parsers is the #1 wanted community contribution
- Discord or GitHub Discussions for support

---

_Last updated: 2026-04-11_
_Status: Planning — Phase 1 not started_
