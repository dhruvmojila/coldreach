# Discovery Sources

ColdReach runs all enabled sources concurrently and merges results. Each source contributes a `confidence_hint` that feeds into the final email score.

---

## Website Crawler

**Source ID:** `website/*`  
**Requires:** Nothing — built-in  
**Speed:** Fast (1–3s per page, ~10s total)

Fetches the company's public pages and extracts email addresses using three methods:

1. `mailto:` link extraction (highest quality — explicit intent)
2. RFC 5322 email regex
3. Obfuscated patterns (`hello [at] example.com`, `hello(at)example.com`)

**Pages crawled:** homepage, `/contact`, `/contact-us`, `/team`, `/our-team`, `/about`, `/about-us`, `/people`, `/staff`, `/leadership`, `/management`, `/company`

**Confidence hints by page:**

| Page type | Confidence delta |
| --------- | ---------------- |
| Contact page | +35 |
| Team / people page | +30 |
| About page | +25 |
| Homepage / other | +15 |

**Skip with:** `--no-web`

---

## WHOIS

**Source ID:** `whois`  
**Requires:** Nothing — built-in  
**Speed:** Fast (1–2s)

Queries the WHOIS registry for the domain's registrant and administrative contact email. Often masked by privacy services (WhoisGuard, Domains by Proxy), but useful for smaller companies.

**Skip with:** `--no-whois`

---

## GitHub

**Source ID:** `github/commit`, `github/profile`  
**Requires:** Nothing — uses unauthenticated GitHub API  
**Speed:** Fast (2–5s)

Searches GitHub for repositories matching the company domain, then mines commit history for author email addresses. Also checks organization member profiles for public email fields.

!!! tip
    Works best for tech companies and developer tools where founders/employees commit publicly.

**Rate limiting:** The unauthenticated GitHub API allows 60 requests/hour. ColdReach respects this — add a `GITHUB_TOKEN` env var to the token if you hit limits.

**Skip with:** `--no-github`

---

## Reddit

**Source ID:** `reddit`  
**Requires:** Nothing — uses Reddit JSON API  
**Speed:** Fast (1–3s)

Searches Reddit for posts mentioning the company domain and extracts any email addresses from post bodies and comments. Useful for finding support contacts or founders who have posted publicly.

**Skip with:** `--no-reddit`

---

## Search Engine (SearXNG / DDG)

**Source ID:** `search`  
**Requires:** `docker compose up searxng` for SearXNG; DDG and Brave are fallbacks  
**Speed:** Medium (3–8s)

Performs web searches for the domain with email-targeted queries (e.g. `site:acme.com email contact`). Falls back automatically:

1. SearXNG (self-hosted, 40+ engines) — preferred
2. DuckDuckGo Lite — if SearXNG unavailable
3. Brave Search — final fallback

**Skip with:** `--no-search`

---

## theHarvester

**Source ID:** `osint/theharvester`  
**Requires:** `docker compose up theharvester`  
**Speed:** Slow (15–60s depending on sources)

Runs [theHarvester](https://github.com/laramies/theHarvester) — a mature OSINT tool that searches certificate transparency logs, Bing, Google dorks, PGP keyservers, and more. ColdReach calls the theHarvester REST API running in Docker.

Best for: finding emails that have appeared in public records or search engine indexes.

**Skip with:** `--no-harvester` or `--quick`

---

## SpiderFoot

**Source ID:** `osint/spiderfoot`  
**Requires:** `docker compose up spiderfoot`  
**Speed:** Slow (30–120s)

Runs [SpiderFoot](https://github.com/smicallef/spiderfoot) — a deep OSINT framework that correlates WHOIS, DNS records, social networks, threat intel feeds, and web crawling into a unified graph. ColdReach submits a scan via the SpiderFoot REST API and polls for results.

Best for: thorough investigations where accuracy matters more than speed.

**Skip with:** `--no-spiderfoot` or `--quick`

---

## Pattern Generator

**Source ID:** `pattern/generated`  
**Requires:** `--name "First Last"` to be specified  
**Speed:** Instant

Not a network source — generates likely email addresses from a person's name and the company's inferred email format. See [Pattern Generation](how-it-works.md#pattern-generation) for the full algorithm.

Patterns are verified through the pipeline like any discovered email; their initial confidence is lower than directly found emails.

---

## Source comparison

| Source | Speed | Accuracy | Docker required |
| ------ | ----- | -------- | --------------- |
| Website crawler | Fast | High | No |
| WHOIS | Fast | Low–Medium | No |
| GitHub | Fast | Medium (tech companies) | No |
| Reddit | Fast | Low | No |
| Search engine | Medium | Medium | No (DDG fallback) |
| theHarvester | Slow | Medium–High | Yes |
| SpiderFoot | Slow | High | Yes |
| Pattern generator | Instant | Low–Medium | No (needs `--name`) |

!!! tip "Use `--quick` for most lookups"
    `--quick` skips theHarvester and SpiderFoot, giving you results in under 15 seconds.
    Run without `--quick` only when you need maximum coverage.
