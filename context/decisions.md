# Decisions Log

Record decisions that affect architecture, tooling, workflow, or team conventions.

### [2026-04-25 09:45 UTC-4] File-based cross-agent context protocol

- Context:
  - Project work is split between Cursor and Claude Code due to usage limits.
  - Agent switching caused risk of stale or missing context.
- Decision:
  - Adopt a repo-committed protocol with mandatory files: `CONTEXT_MANAGEMENT.md`, `context/current-task.md`, `context/handoff.md`, `context/decisions.md`, plus graph outputs.
- Alternatives considered:
  - Rely on chat history only (rejected: non-portable and inconsistent).
  - Keep handoff docs outside repo (rejected: not visible to counterpart agent by default).
- Consequences:
  - Slight manual overhead each session.
  - Significant reduction in context drift when swapping agents or machines.
- Owner:
  - Repo maintainer

## Template

### [YYYY-MM-DD HH:MM TZ] Decision title

- Context:
- Decision:
- Alternatives considered:
- Consequences:
- Owner:


### [2026-04-25 09:42 EDT] Session close decisions

- Use scripts/session_close.py as mandatory end-of-session workflow for both agents

### [2026-04-25 10:13 EDT] Session close decisions

- Firecrawl is a separate-stack optional add-on — not in default docker-compose; status shows it separately from core services
- Reacher health check uses TCP probe (bash /dev/tcp) not HTTP GET — the service has no HTTP root endpoint by design
- scripts/setup.sh is now the canonical first-time setup path — handles prereqs, clone, build, wait-for-healthy, verify

### [2026-04-25 12:27 EDT] Session close decisions

- API defaults to quick=true for extension requests (10s target); SSE stream endpoint separate from blocking JSON endpoint

### [2026-04-25 15:54 EDT] Session close decisions

- Two separate Vite configs for content (IIFE) and service-worker (ESM) — Rollup cannot mix inlineDynamicImports with multiple inputs
- Icons are SVG for development; production needs PNG conversion before Chrome Web Store submission

### [2026-04-25 16:14 EDT] Session close decisions

- API quick default changed False (all core sources) — extension defaults to Standard mode; Quick/Full selectable in popup
- start SSE event emitted before sources run — gives extension total_sources count for 0-100% progress calculation

### [2026-04-26 17:59 EDT] Session close decisions

- SpiderFoot: explicit -m module list beats -u passive — passive triggers port scanners, DNS brute-force, Tor crawlers that never finish
- Container timeout binary (not proc.kill) is the correct way to kill docker exec subprocesses — proc.kill only stops the local client

### [2026-04-26 18:14 EDT] Session close decisions

- theHarvester container runs restfulHarvest REST server — docker exec theHarvester fails because theHarvester CLI is not on PATH in that entrypoint context; HTTP API is the correct integration
- SpiderFoot runs Alpine Linux (busybox timeout) not Debian — --signal=SIGTERM --kill-after=10 are GNU coreutils flags that fail on Alpine; use timeout -s TERM SECONDS instead

### [2026-04-26 18:38 EDT] Session close decisions

- SpiderFoot -x (strict mode) was wrong — email modules chain through INTERNET_NAME events derived from DOMAIN_NAME, so -x excludes them. Use -m explicit list without -x.
- theHarvester source param must be repeated (source=X&source=Y) not comma-joined. bing is not a valid source name — removed from _FREE_SOURCES.
- SpiderFoot JSON output format is type=Email Address (with space), not EMAILADDR. Parser updated to accept both.

### [2026-04-26 20:21 EDT] Session close decisions

- SearXNG wikidata engine crashes with KeyError on every request — disabled in settings.yml. Now returns results from bing/duckduckgo/google/brave/qwant.
- SpiderFoot: only sfp_pgp,sfp_emailformat,sfp_whois,sfp_email. sfp_spider and sfp_duckduckgo cause 50-minute runs. sfp_pgp alone finds 20+ emails in 60s via PGP keyservers.
- Background scanning: _SLOW_SOURCE_NAMES frozenset marks spiderfoot/theharvester as background. fast sources run+return in 30s. SSE stream uses background_slow=True so extension shows fast results immediately.

### [2026-05-02 09:40 EDT] Session close decisions

- SpiderFoot: REST API polling (POST /startscan → poll /scaneventresults → GET /stopscan) replaces docker exec — no orphaned scans, real-time results
- Job system v2: SSE stays open until ALL sources done; emails appear one-at-a-time; Stop button properly cancels scan

### [2026-05-02 10:18 EDT] Session close decisions

- Chrome extension popups close when unfocused — SSE connection dies. Fix: background SW runs scan via polling (GET /api/v2/scan/{id} every 3s), stores results in chrome.storage.session. Popup just reads storage, never holds the connection.
- SpiderFoot sfp_citadel returns EMAILADDR_COMPROMISED (breach data) not EMAILADDR — added to _EMAIL_EVENT_TYPES and _parse_output so breach emails (like ajay.raut@flipkart.com [apollo.io]) are now captured

### [2026-05-02 10:49 EDT] Session close decisions

- Web crawler _EMAIL_RE had (?!["'/]) lookahead blocking emails inside JSON strings like 'support@company.com'. Removed strict lookahead — domain filtering handles false positives.
- v2 _run_v2_scan was missing generate_role_emails() call. Role emails (info@, contact@, sales@ etc.) now guaranteed to appear even when all external sources find nothing.
- SearXNG query 'fareleaders.com email contact' returned xnxx.com results. Fixed to '@fareleaders.com', 'fareleaders.com email OR contact', 'site:fareleaders.com' — better signal.

### [2026-05-02 11:06 EDT] Session close decisions

- Company context from SearXNG meta-descriptions (not homepage scrape) — works for JS SPAs like fareleaders.com that return JavaScript code when scraped directly
- intelligent_search classified as slow source — runs after web_crawler/github/whois return fast results; Groq API is async via asyncio.to_thread to avoid blocking

### [2026-05-02 11:44 EDT] Session close decisions

- SpiderFoot _fetch_results was only querying EMAILADDR — sfp_citadel returns EMAILADDR_COMPROMISED (breach data like ajay.raut@flipkart.com [apollo.io]). Now queries all 4 types per scan.
- IntelligentSearch SearXNG pass-1 extracted from snippets (meta-descriptions), pass-2 crawls top 4 domain-URLs from results. Emails live in page bodies, not search snippets.

### [2026-05-02 12:22 EDT] Session close decisions

- SearXNG '@domain' query returns 0 results — search engines don't index @ symbols. Fixed to human-readable queries: 'domain email OR contact', 'company contact email press', 'site:domain contact OR email'.
- SearchEngine and IntelligentSearch now do two-pass: (1) extract emails from SearXNG snippets, (2) crawl domain URLs returned by SearXNG. pressoffice@snapdeal.com found by crawling a SearXNG-indexed page.
- GitHub source tries 7 slug variants (snapdeal, Snapdeal, SNAPDEAL, snapdeal-com, snapdealhq, etc.) since companies like Snapdeal use title-case GitHub orgs.
