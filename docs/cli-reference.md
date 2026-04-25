# CLI Reference

ColdReach exposes five top-level commands: `status`, `serve`, `verify`, `find`, and `cache`.

```
coldreach [OPTIONS] COMMAND [ARGS]...

Options:
  -v, --verbose   Enable debug logging.
  -V, --version   Show version and exit.
  -h, --help      Show help message and exit.
```

---

## `coldreach status`

Check which Docker services are running and which optional packages are installed.

```bash
coldreach status
```

Displays a gradient ASCII banner, then pings all services concurrently and reports:

- **Docker Services** — SearXNG, Reacher, SpiderFoot, theHarvester with live latency and online/offline status
- **Optional Packages** — holehe, crawl4ai, firecrawl-py with install commands
- **Optional add-ons** — Firecrawl (separate stack, not part of default compose)
- **Actionable hints** — exact `docker compose up -d <service>` commands for anything offline

```
╭─ Docker Services  4/4 online ────────────────╮
│  SearXNG    ● ONLINE   84ms   8088  Metasearch ...
│  Reacher    ● ONLINE   55ms   8083  SMTP verifier
│  SpiderFoot ● ONLINE   49ms   5001  OSINT engine
│  theHarvester ● ONLINE 35ms  5050  Harvester
╰──────────────────────────────────────────────╯

  Optional add-ons (separate setup):  ○ Firecrawl

  ✓  All services online — ready for full discovery.
     coldreach find --domain stripe.com --quick
```

!!! tip
    Run `coldreach status` after `docker compose up -d` to confirm all services are healthy before a find run.

---

## `coldreach serve`

Start the local API server for the Chrome extension and scripting tools.

```bash
coldreach serve [OPTIONS]
```

### Options

| Option | Default | Description |
| ------ | ------- | ----------- |
| `--host TEXT` | `127.0.0.1` | Host to bind. Keep as `127.0.0.1` — do not expose to the network. |
| `--port INT` | `8765` | Port to listen on. |
| `--reload` | off | Auto-reload on code changes (development only). |

### Examples

```bash
coldreach serve                        # localhost:8765
coldreach serve --port 9000
coldreach serve --reload               # dev mode
```

Once running, Swagger UI is available at **http://localhost:8765/docs**.

See [API Server](api-server.md) for full endpoint documentation.

---

## `coldreach verify`

Run the verification pipeline for a single email address.

```bash
coldreach verify EMAIL [OPTIONS]
```

### Arguments

| Argument | Description            |
| -------- | ---------------------- |
| `EMAIL`  | Email address to check |

### Options

| Option | Default | Description |
| ------ | ------- | ----------- |
| `--json` | off | Output machine-readable JSON instead of the rich table |
| `--dns-timeout FLOAT` | `5.0` | DNS resolver timeout in seconds |
| `--holehe` | off | Run Holehe platform check (step 5) — checks 120+ platforms, adds ~15–45s |

### Examples

```bash
# Basic verification (syntax + disposable + DNS)
coldreach verify patrick@stripe.com

# Full pipeline with SMTP (requires Reacher Docker service)
coldreach verify patrick@stripe.com

# Add Holehe platform check — best for catch-all domains
coldreach verify info@stripe.com --holehe

# JSON output for scripting
coldreach verify patrick@stripe.com --json
```

### Output

```
  ✓  patrick@stripe.com  confidence 72/100

  Check        Status   Detail
  syntax       pass     Valid RFC 5322 syntax
  disposable   pass     Not a disposable email domain
  dns          pass     Found 5 MX record(s) — aspmx.l.google.com (+4 more)
  reacher      pass     SMTP deliverable (not catch-all)
  holehe       pass     Registered on 4 platform(s): twitter, github, linkedin, producthunt
```

### Exit codes

| Code | Meaning |
| ---- | ------- |
| `0` | Email passed all checks |
| `1` | One or more checks failed (invalid/undeliverable) |
| `2` | Usage error (bad arguments) |

---

## `coldreach find`

Discover email addresses for a company domain, combining all enabled sources.

```bash
coldreach find [OPTIONS]
```

### Options

**Target**

| Option | Description |
| ------ | ----------- |
| `--domain, -d DOMAIN` | Domain to search (e.g. `stripe.com`) |
| `--company, -c NAME` | Company name — used as a domain hint when `--domain` is omitted |
| `--name, -n NAME` | Person full name — narrows results to name-matching patterns |

**Behaviour**

| Option | Default | Description |
| ------ | ------- | ----------- |
| `--quick` | off | Skip slow sources (theHarvester, SpiderFoot) |
| `--all` | off | Show all results including low-confidence |
| `--json` | off | Machine-readable JSON output |
| `--min-confidence INT` | from `.env` | Hide results below this confidence score |

**Speed presets**

| Option | Description |
| ------ | ----------- |
| `--quick` | ~10s — skips theHarvester and SpiderFoot |
| `--full` | ~5min — uses theHarvester with all available sources (API-key sources included) |

**Source toggles**

| Option | Description |
| ------ | ----------- |
| `--no-web` | Skip website crawler |
| `--no-whois` | Skip WHOIS lookup |
| `--no-github` | Skip GitHub commit mining |
| `--no-reddit` | Skip Reddit search |
| `--no-search` | Skip SearXNG / DDG search |
| `--no-harvester` | Skip theHarvester |
| `--no-spiderfoot` | Skip SpiderFoot |
| `--firecrawl` | Enable Firecrawl JS scraping (requires `pip install firecrawl-py` + self-hosted server) |
| `--crawl4ai` | Enable crawl4ai Playwright scraping (requires `pip install crawl4ai && crawl4ai-setup`) |

**Verification**

| Option | Description |
| ------ | ----------- |
| `--no-reacher` | Skip Reacher SMTP verification on discovered emails |
| `--holehe` | Run Holehe platform check on found addresses (slow, ~30s/email) |

**Output & cache**

| Option | Description |
| ------ | ----------- |
| `--output, -o FILE` | Export results to `.csv` or `.json` (format inferred from extension) |
| `--no-cache` | Skip cache read and write entirely |
| `--refresh` | Ignore any cached result and re-fetch from all sources |

### Examples

```bash
# Quick scan — ~10s, skips OSINT tools
coldreach find --domain acme.com --quick

# Full discovery (default, ~2min)
coldreach find --domain acme.com

# All sources including API-key ones (~5min)
coldreach find --domain acme.com --full

# Resolve domain automatically from company name
coldreach find --company "Acme Corp"

# Target a specific person (generates name-pattern emails)
coldreach find --domain acme.com --name "Jane Smith"

# Export results to CSV or JSON
coldreach find --domain acme.com --output leads.csv
coldreach find --domain acme.com --output leads.json

# Force re-discovery (bypass cache)
coldreach find --domain acme.com --refresh

# JSON output — pipe-friendly
coldreach find --domain acme.com --json | jq '.emails[] | select(.confidence > 60)'

# Enable JS-heavy site scraping (optional)
coldreach find --domain acme.com --firecrawl
coldreach find --domain acme.com --crawl4ai

# Skip slow OSINT, keep SMTP verification
coldreach find --domain acme.com --no-harvester --no-spiderfoot
```

### Output

```
  Domain: acme.com   Sources: 6   Found: 3 email(s)   Cached: no

  Email                      Confidence  Source               Verified
  john@acme.com              78          website/contact      SMTP ✓
  j.smith@acme.com           52          pattern: first.last  —
  info@acme.com              35          website/other        catch-all
```

---

## `coldreach cache`

Manage the local result cache (SQLite + optional Redis).

### `coldreach cache list`

Show all cached domains with their expiry status.

```bash
coldreach cache list
```

```
  Domain          Cached At            Expires At           Status
  stripe.com      2024-01-15 10:32     2024-01-22 10:32     valid
  acme.com        2024-01-08 09:15     2024-01-15 09:15     expired
```

### `coldreach cache stats`

Show aggregate cache statistics.

```bash
coldreach cache stats
```

```
  Cache stats:
    Total entries:    12
    Valid (not expired): 9
    Expired:          3
    Cache file: /home/user/.coldreach/cache.db
```

### `coldreach cache clear`

Remove cached results.

```bash
# Clear a specific domain
coldreach cache clear --domain acme.com
coldreach cache clear -d acme.com

# Clear everything
coldreach cache clear
```

!!! warning
    `coldreach cache clear` without `--domain` removes all cached results. The next
    `find` command for any domain will re-run all sources.
