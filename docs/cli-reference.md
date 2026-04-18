# CLI Reference

ColdReach exposes three top-level commands: `verify`, `find`, and `cache`.

```
coldreach [OPTIONS] COMMAND [ARGS]...

Options:
  -v, --verbose   Enable debug logging.
  -V, --version   Show version and exit.
  -h, --help      Show help message and exit.
```

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

**Verification**

| Option | Description |
| ------ | ----------- |
| `--no-reacher` | Skip Reacher SMTP verification on discovered emails |
| `--holehe` | Run Holehe platform check on found addresses (slow) |

**Cache**

| Option | Description |
| ------ | ----------- |
| `--no-cache` | Skip cache read and write entirely |
| `--refresh` | Ignore any cached result and re-fetch from all sources |

### Examples

```bash
# Quick scan — fast, skips OSINT tools
coldreach find --domain acme.com --quick

# Full discovery for a domain
coldreach find --domain acme.com

# Target a specific person
coldreach find --domain acme.com --name "Jane Smith"

# Force re-discovery (bypass cache)
coldreach find --domain acme.com --refresh

# JSON output — pipe-friendly
coldreach find --domain acme.com --json | jq '.emails[] | select(.confidence > 60)'

# Show everything including low-confidence guesses
coldreach find --domain acme.com --all

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
