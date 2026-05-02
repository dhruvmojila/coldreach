# Project Progress Log

---

## [2026-04-25 22:30] — Zero-friction setup: health checks, Makefile, rewritten setup.sh, Firecrawl separation, status/find UI improvements

### What Was Done
- Added Docker health checks to every service (SearXNG, Reacher, SpiderFoot, theHarvester) so `docker compose up --wait` actually works
- Pinned Reacher image from `:latest` to `0.11.6` to prevent silent breaking changes
- Rewrote `scripts/setup.sh` as a full setup wizard with prereq checks, idempotent cloning, build step, wait-for-healthy, and coldreach status verification
- Created `Makefile` with common commands: `make setup`, `make up`, `make down`, `make status`, `make logs`, `make test`, `make lint`, `make fmt`, `make find DOMAIN=...`
- Added `ServiceResult.separate_stack` field to `diagnostics.py`; marked Firecrawl as separate-stack so it no longer appears as a failure in status/find
- `quick_service_check()` now only pings core services — Firecrawl excluded from find-command warnings
- Fixed `coldreach status` to show 4/4 core services cleanly; Firecrawl moved to "Optional add-ons (separate setup)" section
- Fixed Reacher detection: `RemoteProtocolError` (port open, no HTTP root) now correctly treated as ONLINE
- Added `coldreach status` service bar to `coldreach find` so users see what's running before the search
- Added `coldreach status` command with big ASCII banner, animated spinner, per-service latency, and actionable fix hints

### Files Changed
| File | Action | Summary |
|------|--------|---------|
| `docker-compose.yml` | Modified | Health checks on SearXNG/Reacher/SpiderFoot/theHarvester; Reacher pinned to 0.11.6; header clarifies Firecrawl is separate |
| `scripts/setup.sh` | Modified | Full rewrite — prereq checks, idempotent clone, docker build, wait-for-healthy, status verify |
| `Makefile` | Added | Common dev commands with inline help |
| `coldreach/diagnostics.py` | Modified | `ServiceResult.separate_stack` field; `_SERVICES` 4-tuple with bool; `quick_service_check()` skips separate-stack services |
| `coldreach/cli.py` | Modified | `status` splits core vs add-ons; `find` bar only warns on core offline; Reacher `RemoteProtocolError` → online |

### Major Logic / Code Changes
- **Health check strategy**: each service uses the tool available in its base image — SearXNG/SpiderFoot use `wget`, Reacher uses `bash /dev/tcp` TCP probe (no HTTP root endpoint), theHarvester uses `python3 urllib.request`
- **`docker compose up --wait`**: with health checks added, this command now reliably blocks until all services are genuinely ready, not just "started"
- **`separate_stack` field**: cleanly separates Firecrawl (which requires a multi-service Firecrawl stack) from the four core services (SearXNG, Reacher, SpiderFoot, theHarvester). Status shows `4/4 online` instead of confusing `4/5`
- **`quick_service_check()` filter**: find command only pings + warns about core services; removes false Firecrawl-offline warnings that confused users
- **Reacher pinned**: `reacherhq/backend:0.11.6` — the running version from docker inspect; prevents future silent breakage from `:latest` updates

### Notes
- `make setup` is now the recommended first-time setup path — runs everything in sequence
- Firecrawl source (`coldreach/sources/firecrawl.py`) is still wired in as opt-in (`--firecrawl` flag), but the status display no longer treats its absence as a problem
- Next: Phase 3 planning (Chrome extension or API server)

---

## [2026-04-25 21:30] — `coldreach status` command + service bar in find + SpiderFoot/theHarvester timeout increases

### What Was Done
- Added `coldreach/diagnostics.py` — async parallel health checks for all Docker services and optional Python packages
- Added `coldreach status` CLI command: gradient ASCII banner, animated spinner, services table (online/offline/latency), packages table, actionable hints for offline services
- Added compact service status bar to `coldreach find` — shows service availability before searching, warns if a requested service is offline
- Increased SpiderFoot max_wait: 300s → 600s; theHarvester max_wait: 120s → 300s
- Exposed `spiderfoot_max_wait` and `harvester_max_wait` in `FinderConfig`

### Files Changed
| File | Action | Summary |
|------|--------|---------|
| `coldreach/diagnostics.py` | Added | Async service pinger + package checker; `DiagnosticsReport` dataclass |
| `coldreach/cli.py` | Modified | `status` command with Rich Live display; service bar in `find`; banner constants |

### Major Logic / Code Changes
- `diagnostics.run()` pings all services concurrently via `asyncio.gather`; `RemoteProtocolError` treated as online (Reacher has no HTTP root)
- `quick_service_check()` for find command uses 3s timeout to keep find startup fast
- `_BANNER_LINES`/`_BANNER_COLORS` hardcoded ANSI block-art with blue→magenta gradient; no pyfiglet dependency

---

## [2026-04-25 20:00] — Integrate crawl4ai, Firecrawl, and role email sources from other project

### What Was Done
- Ported `firecrawl_tool.py` as `coldreach/sources/firecrawl.py` — proper async BaseSource with sitemap discovery, multi-page scraping, and email extraction via Firecrawl SDK
- Ported `crawl4ai_tool.py` as `coldreach/sources/crawl4ai_source.py` — Playwright JS rendering for SPA sites; fixed broken `config.settings` import and wrong `asyncio.new_event_loop()` pattern
- Added `generate_role_emails()` to `coldreach/generate/patterns.py` — the missing piece from `email_permutator.py` (personal pattern generation was already complete)
- Wired all three into `FinderConfig` and `finder.py`; added `--firecrawl` and `--crawl4ai` CLI flags
- Added `firecrawl_url` back to `config.py` (now properly used by `FirecrawlSource`)

### Files Changed
| File | Action | Summary |
|------|--------|---------|
| `coldreach/sources/firecrawl.py` | Added | BaseSource using Firecrawl SDK + sitemap discovery; httpx for availability/sitemap, `asyncio.to_thread` for SDK calls |
| `coldreach/sources/crawl4ai_source.py` | Added | BaseSource using crawl4ai Playwright renderer; fixed broken sync patterns |
| `coldreach/generate/patterns.py` | Modified | Added `generate_role_emails()` returning info/sales/contact/etc candidates |
| `coldreach/core/finder.py` | Modified | Added imports, `use_firecrawl/use_crawl4ai/use_role_emails` to FinderConfig, wired sources and role email generation |
| `coldreach/config.py` | Modified | Re-added `firecrawl_url` field (now actually used) |
| `coldreach/cli.py` | Modified | Added `--firecrawl` and `--crawl4ai` flags; pass to FinderConfig |

### Major Logic / Code Changes
- **FirecrawlSource**: opt-in (`use_firecrawl=False`); skips gracefully if `firecrawl-py` not installed or server unreachable; `_scrape_with_sdk()` runs sync SDK in `asyncio.to_thread()`
- **Crawl4AISource**: opt-in (`use_crawl4ai=False`); skips if `crawl4ai` not installed; pure async via `AsyncWebCrawler`; junk-content detection filters bot-block pages
- **Role emails**: always-on (`use_role_emails=True`); adds 10 role candidates (info, contact, sales, marketing, etc.) with `confidence_hint=5`; skips any already found by real sources

---

## [2026-04-18 22:00] — Integrate crawl4ai, Firecrawl, and role email sources from other project

### What Was Done
- Ported `firecrawl_tool.py` as `coldreach/sources/firecrawl.py` — proper async BaseSource with sitemap discovery, multi-page scraping, and email extraction via Firecrawl SDK
- Ported `crawl4ai_tool.py` as `coldreach/sources/crawl4ai_source.py` — Playwright JS rendering for SPA sites; fixed broken `config.settings` import and wrong `asyncio.new_event_loop()` pattern
- Added `generate_role_emails()` to `coldreach/generate/patterns.py` — the missing piece from `email_permutator.py` (personal pattern generation was already complete)
- Wired all three into `FinderConfig` and `finder.py`; added `--firecrawl` and `--crawl4ai` CLI flags
- Added `firecrawl_url` back to `config.py` (now properly used by `FirecrawlSource`)

### Files Changed
| File | Action | Summary |
|------|--------|---------|
| `coldreach/sources/firecrawl.py` | Added | BaseSource using Firecrawl SDK + sitemap discovery; httpx for availability/sitemap, `asyncio.to_thread` for SDK calls |
| `coldreach/sources/crawl4ai_source.py` | Added | BaseSource using crawl4ai Playwright renderer; fixed broken sync patterns |
| `coldreach/generate/patterns.py` | Modified | Added `generate_role_emails()` returning info/sales/contact/etc candidates |
| `coldreach/core/finder.py` | Modified | Added imports, `use_firecrawl/use_crawl4ai/use_role_emails` to FinderConfig, wired sources and role email generation |
| `coldreach/config.py` | Modified | Re-added `firecrawl_url` field (now actually used) |
| `coldreach/cli.py` | Modified | Added `--firecrawl` and `--crawl4ai` flags; pass to FinderConfig |

### Major Logic / Code Changes
- **FirecrawlSource**: opt-in (`use_firecrawl=False`); skips gracefully if `firecrawl-py` not installed or server unreachable; `_scrape_with_sdk()` runs sync SDK in `asyncio.to_thread()`
- **Crawl4AISource**: opt-in (`use_crawl4ai=False`); skips if `crawl4ai` not installed; pure async via `AsyncWebCrawler`; junk-content detection filters bot-block pages
- **Role emails**: always-on (`use_role_emails=True`); adds 10 role candidates (info, contact, sales, marketing, etc.) with `confidence_hint=5`; skips any already found by real sources
- **email_permutator.py assessment**: coldreach already has a superior pattern system (`generate/patterns.py` + `learner.py`); role emails were the only missing piece

### Notes
- Both crawl4ai and firecrawl are opt-in to keep the default run fast; enable with `--crawl4ai` / `--firecrawl`
- 363 tests pass, 7 skipped (holehe)

---

## [2026-04-18 21:30] — Fix critical status bug: map Reacher results to VerificationStatus; fix confidence scoring; remove dead Firecrawl config

### What Was Done
- Fixed `finder.py`: emails verified by Reacher now show `valid`, `catch_all`, or `undeliverable` instead of always `unknown`
- Fixed confidence scoring: changed `max()` of source hints to cumulative `sum()` so multiple sources confirming the same email raise confidence
- Removed dead `firecrawl_url` config field from `config.py` (Firecrawl was never integrated, Docker image requires extra setup)

### Files Changed
| File | Action | Summary |
|------|--------|---------|
| `coldreach/core/finder.py` | Modified | Status mapping now uses `pipeline.checks["reacher"]` to set VALID/CATCH_ALL/UNDELIVERABLE; confidence uses sum not max |
| `coldreach/config.py` | Modified | Removed `firecrawl_url` field |

### Major Logic / Code Changes
- **Status mapping** (`finder.py` lines 262-280): Added `reacher_check = pipeline.checks.get("reacher")`. Priority: FAIL → INVALID, reacher.passed → VALID, reacher.warned → CATCH_ALL, reacher.failed → UNDELIVERABLE, mx_records → UNKNOWN, else → RISKY
- **Confidence scoring**: `max_hint` replaced with `source_hint = sum(sr.confidence_hint for sr in source_results)` — multiple discovery sources now stack their hints cumulatively
- **Firecrawl removal**: The `firecrawl_url` field in `ColdReachConfig` was never read by any source module; removed to avoid confusion

### Notes
- 363 tests pass, 7 skipped (holehe optional extra not installed)
- `firecrawl_tool.py` in project root is a stale scratch file not imported by any `coldreach/` module — can be deleted separately

---

## [2026-04-18 20:00] — Add company→domain resolver, CSV/JSON export, holehe skip marker

### What Was Done
- Created `coldreach/resolve/company.py` — resolves company name to domain via Clearbit Autocomplete (primary) + DDG Lite (fallback); no API keys required
- Created `coldreach/export/writer.py` — exports `DomainResult` to `.csv` or `.json`; format inferred from extension
- Wired both into `coldreach/cli.py`: `--company "Stripe"` auto-resolves domain before find; `--output leads.csv` exports results after find
- Added `requires_holehe` skip marker to `test_verify_holehe.py` — 7 tests now skip cleanly when holehe optional extra is not installed (CI installs it via `--all-extras`; local dev doesn't need to)
- Fixed duplicate data file warning in wheel build (removed redundant `force-include` from `pyproject.toml`)
- Added `tags: ["v*"]` trigger to `ci.yml` so PyPI publish fires on version tag pushes

### Files Changed
| File | Action | Summary |
|------|--------|---------|
| `coldreach/resolve/__init__.py` | Added | Package init, exports `resolve_domain` |
| `coldreach/resolve/company.py` | Added | Company→domain resolver (Clearbit + DDG fallback) |
| `coldreach/export/__init__.py` | Added | Package init, exports `export_results` |
| `coldreach/export/writer.py` | Added | CSV and JSON export for `DomainResult` |
| `coldreach/cli.py` | Modified | Added `--output` flag, company resolution before find |
| `tests/unit/test_resolve_company.py` | Added | 16 tests for resolver (all HTTP mocked with respx) |
| `tests/unit/test_export_writer.py` | Added | 20 tests for CSV/JSON export (all using tmp_path) |
| `tests/unit/test_verify_holehe.py` | Modified | Added `requires_holehe` skip marker |

### Major Logic / Code Changes
- `--company "Stripe"` flow: resolves domain first (prints "Resolving…" + "→ stripe.com"), then runs find as normal
- Extension validation on `--output` happens before the slow find runs (fail fast)
- Clearbit Autocomplete is free, no key, returns JSON array; first result's `domain` field is used
- DDG fallback posts to `duckduckgo.com/lite/`, parses href attributes, skips noise domains (LinkedIn, Twitter, etc.)
- Export appends a confirmation line after the results table when not in `--json` mode

---

## [2026-04-18 18:30] — Add MkDocs documentation site with GitHub Pages deployment

### What Was Done
- Added `docs` dependency group to `pyproject.toml` (`mkdocs`, `mkdocs-material`, `mkdocstrings[python]`, `mkdocs-autorefs`)
- Created `mkdocs.yml` — Material theme, NumPy docstring style, strict build, full nav
- Created `docs/` with 6 content pages + 6 API reference pages auto-generated from docstrings
- Created `.github/workflows/docs.yml` — deploys to GitHub Pages on push to main
- Fixed `coldreach/core/models.py` Pydantic model docstrings: `Parameters` → `Attributes` (griffe requires `Attributes` for class fields)
- Added `site/` to `.gitignore`
- Trimmed `README.md` to ~50 lines — overview + install + links to docs site

### Files Changed
| File | Action | Summary |
|------|--------|---------|
| `mkdocs.yml` | Added | MkDocs configuration — Material theme, mkdocstrings, nav |
| `pyproject.toml` | Modified | Added `docs` dependency group |
| `.github/workflows/docs.yml` | Added | GitHub Pages deployment on push to main |
| `docs/index.md` | Added | Landing page with comparison table and feature cards |
| `docs/getting-started.md` | Added | Full step-by-step install guide |
| `docs/cli-reference.md` | Added | Complete CLI reference for all commands |
| `docs/configuration.md` | Added | Full `.env` reference |
| `docs/how-it-works.md` | Added | Pipeline diagrams, scoring table, cache architecture |
| `docs/sources.md` | Added | All 8 discovery sources with speed/accuracy comparison |
| `docs/api/index.md` | Added | API overview with usage example |
| `docs/api/models.md` | Added | Auto-generated from `coldreach.core.models` |
| `docs/api/verify.md` | Added | Auto-generated from `coldreach.verify.*` |
| `docs/api/sources.md` | Added | Auto-generated from `coldreach.sources.*` |
| `docs/api/generate.md` | Added | Auto-generated from `coldreach.generate.*` |
| `docs/api/storage.md` | Added | Auto-generated from `coldreach.storage.*` and `coldreach.core.finder` |
| `coldreach/core/models.py` | Modified | `Parameters` → `Attributes` in Pydantic model docstrings |
| `.gitignore` | Modified | Added `site/` build output |
| `README.md` | Modified | Trimmed to 50-line overview with link to docs site |

### Major Logic / Code Changes
- MkDocs `--strict` mode enabled: build fails if any warning is raised — ensures docs stay in sync with code
- `mkdocstrings` uses griffe for static analysis (no runtime import) — optional deps missing is fine
- API reference pages auto-update when docstrings change — zero maintenance overhead

### Notes
- `site/` is gitignored; GitHub Pages is deployed via CI only
- MkDocs 2.0 compatibility warning from Material team is a banner (not a build warning) — not treated as strict failure
- To preview locally: `uv run mkdocs serve`
- To deploy manually: `uv run mkdocs gh-deploy`

---

## [2026-04-18 17:30] — Rewrite README.md for Phase 1 completion

### What Was Done
- Rewrote README.md from scratch with accurate Phase 1 content
- Fixed stale ports in services table (5432→5433, 6379→6380, 8080→8088)
- Removed references to Firecrawl (not implemented) and Phase 2 placeholder commands
- Added correct install flow: clone → setup.sh → docker compose build → docker compose up → pip install
- Added full CLI reference for `verify`, `find` (all flags), and `cache` subcommands
- Updated project status: Phase 1 marked complete, Phase 2 as next
- Added discovery sources table with correct `Requires` column
- Added pattern generation + Holehe/Reacher to How It Works section

### Files Changed
| File | Action | Summary |
|------|--------|---------|
| `README.md` | Modified | Full rewrite — accurate ports, correct install flow, complete CLI reference, Phase 1 status |

### Major Logic / Code Changes
- No code changes — documentation only

---

## [2026-04-18 15:00] — Add domain format learner + wire pattern generation into find_emails()

### What Was Done
- Created `coldreach/generate/learner.py` — `learn_format()` wraps `most_likely_format()` with logging; `targeted_patterns()` generates only the domain's inferred format (+ companion) instead of all 12
- Wired learner into `find_emails()`: after sources return, if `person_name` given → infer format from found emails → append targeted `SourceResult(source=PATTERN_GENERATED)` candidates
- Confidence hint: +10 when format inferred from real emails, +5 for blind fallback guesses
- Fallback when format unknown: top-3 B2B formats (`first.last`, `flast`, `first`)
- 334 tests passing, ruff + mypy clean

### Files Changed
| File | Action | Summary |
|------|--------|---------|
| `coldreach/generate/learner.py` | Added | `learn_format()` + `targeted_patterns()` |
| `coldreach/core/finder.py` | Modified | Pattern generation step after sources; appends to `all_raw` before dedup/verify |
| `tests/unit/test_generate_learner.py` | Added | 17 tests: format detection, targeted generation, companion formats, fallback, edge cases |

### Major Logic / Code Changes
- **Companion formats**: `first.last` always includes `flast` companion (and vice versa) — these two dominate B2B email patterns and often coexist
- **Format inference order**: inferred format comes first in output, companions second — preserves confidence ordering
- **No shotgun generation**: `coldreach find --domain acme.com --name "John Smith"` now generates ≤3 candidates (vs 12 before), all matching the company's real pattern
- **Integration point**: generated candidates join the same dedup + verification pipeline as discovered emails; pipeline scores them independently

---

## [2026-04-18 14:15] — Add SQLite/Redis cache layer + cache CLI subcommand

### What Was Done
- Created `coldreach/storage/cache.py` — two-layer cache (SQLite always-on + optional Redis); 7-day TTL; Pydantic JSON round-trip for `DomainResult`
- Created `coldreach/storage/__init__.py`
- Wired `CacheStore` into `find_emails()`: checks cache on entry (skips all sources on hit), stores result after scan; `refresh_cache` flag bypasses read but still overwrites
- Added `cache_db`, `redis_url`, `cache_ttl_days`, `use_cache`, `refresh_cache` fields to `FinderConfig`
- Added `--no-cache` and `--refresh` flags to `coldreach find`
- Added `coldreach cache list|clear|stats` subcommand group to CLI
- 317 tests passing, ruff + mypy clean

### Files Changed
| File | Action | Summary |
|------|--------|---------|
| `coldreach/storage/__init__.py` | Added | Package init, exports CacheStore |
| `coldreach/storage/cache.py` | Added | CacheStore with SQLite + optional Redis, 7-day TTL |
| `coldreach/core/finder.py` | Modified | Cache lookup/store in find_emails(); new FinderConfig fields |
| `coldreach/cli.py` | Modified | `--no-cache`, `--refresh` flags; `cache list/clear/stats` subcommands |
| `tests/unit/test_storage_cache.py` | Added | 18 tests covering hit/miss/expiry/clear/list/stats/Redis-fallback |

### Major Logic / Code Changes
- **Cache-first pattern**: `find_emails()` checks SQLite (then Redis) before running any source; on hit returns immediately with `min_confidence` filter applied
- **Store before filter**: full result (all emails) is stored in cache, then `min_confidence` is applied — future calls with different thresholds still work
- **Redis optional**: uses `redis.Redis.from_url()` with ping check; if unavailable, silently falls back to SQLite only
- **TTL stored as Unix timestamp**: `expires_at = time.time() + ttl_seconds`; expired rows deleted on read (lazy eviction)
- **CLI cache subcommand**: `coldreach cache list` shows domain + cache timestamp + expired status; `clear` returns row count; `stats` shows total/valid/expired

---

## [2026-04-18 13:30] — Add Holehe platform check + wire Reacher into verification pipeline

### What Was Done
- Created `coldreach/verify/holehe.py` — calls holehe's 120+ platform checkers programmatically via asyncio (no trio dependency, runs modules directly with httpx.AsyncClient + semaphore)
- Extended `run_basic_pipeline()` with optional Reacher SMTP step (step 4) and Holehe platform step (step 5); both are no-ops when disabled so existing behavior is unchanged
- Added `reacher_url`, `use_reacher`, `use_holehe` fields to `FinderConfig`; `find_emails()` now passes them to the pipeline
- Added `--no-reacher` and `--holehe` flags to the `find` CLI command
- 299 tests passing, ruff + mypy clean

### Files Changed
| File | Action | Summary |
|------|--------|---------|
| `coldreach/verify/holehe.py` | Added | Programmatic holehe check; +15 for ≥2 platforms, +5 for 1 |
| `coldreach/verify/pipeline.py` | Modified | Added Reacher + Holehe as optional steps 4 and 5 |
| `coldreach/core/finder.py` | Modified | `FinderConfig` gets `reacher_url`, `use_reacher`, `use_holehe`; passed to pipeline |
| `coldreach/cli.py` | Modified | `--no-reacher` and `--holehe` flags wired through to `FinderConfig` |
| `tests/unit/test_verify_holehe.py` | Added | 8 tests covering pass/warn/skip/exception/threshold cases |

### Major Logic / Code Changes
- **Pipeline now 5 steps**: syntax → disposable → DNS → Reacher (optional) → Holehe (optional)
- **Reacher is on by default** (`use_reacher=True`, `reacher_url="http://localhost:8083"`); gracefully SKIPs if container not running
- **Holehe is opt-in** (`use_holehe=False` by default) — slow (15-45s per email), enable with `--holehe`
- **Holehe score**: +15 if registered on ≥2 platforms, +5 for 1, WARN+0 for none — never hard-fails
- **holehe programmatic API**: `import_submodules("holehe.modules")` + `get_functions()` gives module list; each module is `async def(email, client, out)` compatible with asyncio httpx

---

## [2026-04-18 12:00] — Rewrite HarvesterSource to CLI, add quick/full modes, fix HTML entity emails

### What Was Done
- Rewrote `HarvesterSource` entirely: dropped REST API approach, switched to `docker exec theHarvester` CLI with `-f /tmp/output` JSON file output (same pattern as SpiderFoot CLI rewrite)
- Added `_HTML_ENTITY_PREFIX_RE` to filter JS unicode-escape artifacts (`u003caccount@domain.com`) in both harvester and web crawler
- Added `--quick` and `--full` CLI flags to `coldreach find`: quick skips harvester+spiderfoot (~10s), default uses free harvester sources (~2min), full uses `-b all` (~5min)
- Added `harvester_sources` field to `FinderConfig` to pass `"all"` in full mode
- Added `--no-spiderfoot` toggle alongside existing `--no-harvester`
- Removed `-x` (strict) flag from SpiderFoot CLI — it blocked chained module execution and returned 0 emails
- Rewrote `tests/unit/test_sources_harvester.py` to match new CLI-based interface
- 291 tests passing, ruff + mypy clean
- Live test confirmed: `coldreach find --domain kayak.com --quick` returns 12 emails in ~5s

### Files Changed
| File | Action | Summary |
|------|--------|---------|
| `coldreach/sources/harvester.py` | Rewritten | CLI-based via `docker exec theHarvester -f /tmp/output`; reads JSON output file |
| `coldreach/sources/web_crawler.py` | Modified | Added HTML entity prefix filter in `_add()` |
| `coldreach/core/finder.py` | Modified | Added `harvester_sources`, `use_spiderfoot` fields to `FinderConfig` |
| `coldreach/cli.py` | Modified | Added `--quick`, `--full`, `--no-spiderfoot` flags; mode tag display |
| `tests/unit/test_sources_harvester.py` | Rewritten | 20 tests for CLI-based interface incl. timeout, docker-not-found, HTML entity filter |

### Major Logic / Code Changes
- **HarvesterSource._run_cli**: `docker exec coldreach-theharvester theHarvester -d <domain> -b <sources> -l 500 -q -f /tmp/cr-<domain>` → reads `/tmp/cr-<domain>.json` via second `docker exec cat`
- **HarvesterSource._filter_emails**: lowercase → regex validate → HTML entity check → domain filter → dedup
- **_HTML_ENTITY_PREFIX_RE**: `r"^u[0-9a-f]{3,4}"` — catches `u003c` (`<`), `u002f` (`/`) etc. from JS unicode escapes
- **Quick mode**: `--quick` sets `no_harvester=True, no_spiderfoot=True` — only fast HTTP sources run
- **Full mode**: `--full` passes `harvester_sources="all"` → CLI gets `-b all`; default passes free sources list

### Notes
- SpiderFoot still takes 5+ minutes for large domains; `--quick` is the recommended default for interactive use
- `_FREE_SOURCES` list contains 15 sources that work without API keys

---

## [2026-04-12 20:40] — Fix all sources: SearXNG config, harvester params, SpiderFoot CLI rewrite

### What Was Done
- Created `config/searxng/settings.yml` (directory was owned by Docker's UID 977, written via `docker run alpine`) — enables JSON search format that our API client requires
- Fixed theHarvester `_FREE_SOURCES`: removed `bing` (not in this version's source list), added `commoncrawl`, `waybackarchive`, `sublist3r`, `robtex`, `yahoo`, `baidu`, `threatcrowd`
- Fixed theHarvester params format: changed from CSV string (`source=bing%2Cduckduckgo`) to repeated params (`source=bing&source=duckduckgo`) — FastAPI endpoint declares `source` as `List[str]`
- Rewrote `SpiderFootSource` entirely: dropped CherryPy web API (broken — `usecase=footprint` finds zero modules in container config), switched to `docker exec` + `sf.py` CLI (same approach as reference `spiderfoot_tool.py`)
- Remapped Docker host ports to avoid clashing with local dev services (postgres→5433, redis→6380, searxng→8088, theharvester→5050)
- Updated `FinderConfig` defaults to match new ports (`searxng_url=:8088`, `harvester_url=:5050`), `spiderfoot_url` replaced with `spiderfoot_container` name
- Removed temp reference files (`spiderfoot_tool.py`, `theharvester_tool.py`)
- 280 unit tests passing, ruff + mypy clean

### Files Changed
| File | Action | Summary |
|------|--------|---------|
| `coldreach/sources/spiderfoot.py` | Rewritten | CLI-based via `docker exec sf.py` — no more web API |
| `coldreach/sources/harvester.py` | Modified | Fixed `_FREE_SOURCES` list; params as `list[tuple]` for repeated keys |
| `coldreach/core/finder.py` | Modified | `spiderfoot_url` → `spiderfoot_container`; harvester timeout 60→120s |
| `docker-compose.yml` | Modified | Remapped ports to avoid local dev conflicts |
| `config/searxng/settings.yml` | Added | SearXNG config with JSON format enabled |
| `tests/unit/test_sources_spiderfoot.py` | Rewritten | 20 tests for new CLI-based interface |
| `tests/unit/test_sources_harvester.py` | Modified | Updated `_FREE_SOURCES` reference |
| `tests/unit/test_config.py` | Modified | Fixed `pytest.raises(Exception)` → `pytest.raises(ValidationError)` |

### Major Logic / Code Changes
- **SpiderFoot CLI command**: `docker exec -w /home/spiderfoot coldreach-spiderfoot /opt/venv/bin/python sf.py -s <domain> -t EMAILADDR -u passive -o json -f -q` — `-f` filters output to EMAILADDR events only, `-u passive` avoids active probing
- **SpiderFoot web API root cause**: `POST /startscan?usecase=footprint` iterates `self.config['__modules__']` to build a module list — this dict is empty in the container's CherryPy startup config, so no modules are found and the scan always errors. CLI mode loads modules from the filesystem directly.
- **theHarvester params**: httpx encodes `dict[str, list]` as `source=bing%2Cduckduckgo` (comma URL-encoded as a single value). FastAPI then receives `["bing,duckduckgo"]` as a single item and fails validation. Fix: use `list[tuple[str, str|int|...]]` which httpx encodes as `source=bing&source=duckduckgo`.
- **SpiderFoot scan duration**: passive scans on large domains (stripe.com) can take 5–10+ minutes. `max_wait=300s` (5 min) is a hard cutoff — use `--no-spiderfoot` for fast queries.

### Notes
- SearXNG settings.yml is owned by root inside the Docker volume (written via `docker run alpine`). If recreating from scratch, re-run: `docker run --rm -v ./config/searxng:/etc/searxng alpine sh -c 'cat > /etc/searxng/settings.yml ...'`
- SpiderFoot with `--no-spiderfoot` skips the slow scan; SearXNG + theHarvester + GitHub cover most email discovery needs for known domains
- theHarvester free sources that reliably find emails: `duckduckgo`, `yahoo`, `baidu` (search engine scraping); `crtsh`, `certspotter`, `hackertarget` (subdomain/cert data, rarely finds emails but useful for host discovery)

---

## [2026-04-11 19:30] — SpiderFoot source + harvester REST API rewrite + full test coverage

### What Was Done
- Rewrote `HarvesterSource` from subprocess wrapper to REST API client against theHarvester's `restfulHarvest` FastAPI server
- Built `SpiderFootSource` — full async polling client for SpiderFoot's CherryPy web API
- Rewired `FinderConfig` and CLI `find` command to support both new sources with `--no-harvester` / `--no-spiderfoot` flags
- Rebuilt `docker-compose.yml`: removed Firecrawl (image access denied), added `spiderfoot` and `theharvester` services built from local clones
- Rewrote `tests/unit/test_sources_harvester.py` to match REST API (dropped subprocess mocks)
- Added `tests/unit/test_sources_spiderfoot.py` — 17 new tests covering start/poll/email-fetch/full-path
- All 279 unit tests passing, ruff + mypy clean

### Files Changed
| File | Action | Summary |
|------|--------|---------|
| `coldreach/sources/spiderfoot.py` | Added | SpiderFoot REST API client: start scan → poll → fetch EMAILADDR results |
| `coldreach/sources/harvester.py` | Modified | Rewritten from subprocess to `GET /query` REST API client |
| `coldreach/core/finder.py` | Modified | Added `use_spiderfoot`, `spiderfoot_url`, `harvester_url` to `FinderConfig`; wired both sources |
| `coldreach/cli.py` | Modified | Added `--no-spiderfoot` flag, wired into `FinderConfig` |
| `docker-compose.yml` | Modified | Added spiderfoot + theharvester build-from-local services; removed Firecrawl |
| `tests/unit/test_sources_harvester.py` | Modified | Rewritten for httpx REST API mocks (removed subprocess mocks) |
| `tests/unit/test_sources_spiderfoot.py` | Added | 17 tests: _start_scan, _wait_for_scan, _get_emails, full fetch path |

### Major Logic / Code Changes
- `HarvesterSource._query()`: now calls `GET /query?domain=<d>&source=<csv>&limit=<n>` and reads `data["emails"]`; sources list is joined to CSV string for proper httpx QueryParams typing
- `SpiderFootSource.fetch()`: three-phase async flow — POST `/startscan` (usecase=footprint) → poll GET `/scanstatus` (index 5 = status string) → GET `/scaneventresultsunique?eventType=EMAILADDR`; max wait 300s with 5s poll interval
- `SpiderFootSource._start_scan()`: three fallback strategies for scan ID extraction — JSON body `["SUCCESS", {"id": ...}]`, redirect `Location` header, raw body regex
- `SpiderFootSource._get_emails()`: HTML-unescapes `&#64;` / `&amp;` before domain-filtering; result deduped via `seen` set
- Both sources return empty results gracefully when Docker services are not running (ConnectError caught and logged at DEBUG)
- `docker-compose.yml` theharvester: ports `5000:80` (FastAPI runs on 80 inside container); volume-mounts `api-keys.yaml` and `proxies.yaml` read-only so keys can be edited without rebuilding

### Removed / Deprecated
- `HarvesterSource` subprocess-based implementation (removed `_is_available()`, `asyncio.create_subprocess_exec`, `_parse_emails()` helper)
- `_FREE_SOURCES` list entry `"thc"` kept but `source` param now sent as CSV string instead of list
- Firecrawl removed from `docker-compose.yml` — `ghcr.io/mendableai/firecrawl` image returns 403; their self-hosted stack requires multiple services beyond a single compose entry

### Notes
- theHarvester REST API docs: `http://localhost:5000/docs` — Swagger UI available once service is up
- SpiderFoot Web UI: `http://localhost:5001/` — scan results browsable after `coldreach find` runs
- `docker compose build spiderfoot theharvester` required on first run (builds from local clones in `./spiderfoot/` and `./theHarvester/`)

---

## [2026-04-11] — Phase 2 complete: all sources, pattern generator, catch-all, Reacher SMTP

### What Was Done
- `SearchEngineSource`: SearXNG → DuckDuckGo Lite → Brave API fallback chain
- `HarvesterSource`: theHarvester subprocess wrapper, skips gracefully if not installed
- `generate/patterns.py`: 12-format email pattern generator with unicode/accent/suffix normalisation
- `generate/patterns.py`: `most_likely_format()` infers domain format from known emails
- `verify/catchall.py`: catch-all domain probe via Reacher with per-session cache
- `verify/reacher.py`: full Reacher SMTP client — deliverable/catch-all/full-inbox/disabled handling
- `core/finder.py`: wired all 6 sources into `FinderConfig`; `--no-search` / `--no-harvester` CLI flags added
- 259 unit tests passing, ruff + mypy clean

### Files Changed
| File | Action | Summary |
|------|--------|---------|
| `coldreach/sources/search_engine.py` | Added | SearXNG/DDG/Brave fallback search source |
| `coldreach/sources/harvester.py` | Added | theHarvester subprocess wrapper |
| `coldreach/generate/__init__.py` | Added | Package init |
| `coldreach/generate/patterns.py` | Added | 12-format pattern generator + format inferrer |
| `coldreach/verify/catchall.py` | Added | Catch-all detection via Reacher probe + cache |
| `coldreach/verify/reacher.py` | Added | Reacher SMTP verification client |
| `coldreach/core/finder.py` | Modified | Added search_engine + harvester sources to pipeline |
| `coldreach/cli.py` | Modified | Added --no-search / --no-harvester flags |
| `tests/unit/test_generate_patterns.py` | Added | 20 pattern generator tests |
| `tests/unit/test_verify_reacher.py` | Added | 14 Reacher client tests |
| `tests/unit/test_verify_catchall.py` | Added | 11 catch-all detection tests |
| `tests/unit/test_sources_harvester.py` | Added | 7 harvester tests |
| `tests/unit/test_sources_search_engine.py` | Added | 8 search engine tests |

### Major Logic / Code Changes
- `SearchEngineSource._run_query()`: tries backends in order, returns first non-empty result
- `HarvesterSource`: uses `shutil.which()` to detect installation, silent skip if absent
- Pattern generator: strips unicode accents, splits hyphens, drops middle names + suffixes before expanding 12 formats
- `check_catchall()`: probes with a `cr-probe-<random20>@domain` address; caches result per domain for session lifetime
- `_parse_reacher_response()`: maps Reacher JSON fields to CheckResult — handles 5 distinct SMTP states

---

## [2026-04-11] — Phase 2: sources layer + find_emails() orchestrator + CLI find command

### What Was Done
- Built `coldreach/sources/` package with `BaseSource` ABC and 3 concrete sources
- `WebCrawlerSource`: crawls `/contact`, `/team`, `/about` etc. with httpx, regex + mailto + obfuscation extraction, asset-TLD filter
- `WhoisSource`: python-whois in thread executor, filters privacy-proxy emails
- `GitHubSource`: mines public commits via GitHub REST API, filters noreply + off-domain emails
- `RedditSource`: Reddit JSON API (no auth), 1 req/s rate limit, extracts domain emails from posts
- `core/finder.py`: `find_emails()` orchestrator — runs all sources concurrently via `asyncio.gather`, merges results, runs verification pipeline, returns ranked `DomainResult`
- `cli.py` `find` command: full implementation with `--no-web/whois/github/reddit`, `--min-confidence`, `--json`, `--timeout`, Rich table output
- 58 new unit tests (192 total, all passing); ruff + mypy clean

### Files Changed
| File | Action | Summary |
|------|--------|---------|
| `coldreach/sources/__init__.py` | Added | Package init |
| `coldreach/sources/base.py` | Added | BaseSource ABC, SourceResult, SourceSummary |
| `coldreach/sources/web_crawler.py` | Added | httpx crawler, regex + mailto + obfuscation extraction |
| `coldreach/sources/whois_source.py` | Added | WHOIS registrant email extraction |
| `coldreach/sources/github.py` | Added | GitHub commit email mining |
| `coldreach/sources/reddit.py` | Added | Reddit JSON API email search |
| `coldreach/core/finder.py` | Added | find_emails() orchestrator with FinderConfig |
| `coldreach/cli.py` | Modified | Replaced find stub with full implementation |
| `tests/unit/test_sources_base.py` | Added | 13 tests for BaseSource/SourceResult |
| `tests/unit/test_sources_web_crawler.py` | Added | 14 tests for crawler + helpers |
| `tests/unit/test_sources_github.py` | Added | 16 tests for GitHub source |
| `tests/unit/test_sources_reddit.py` | Added | 15 tests for Reddit source |

### Major Logic / Code Changes
- `BaseSource.run()` is a safe wrapper — never raises, catches all exceptions and returns empty list + error summary
- `find_emails()` scores = pipeline.score + max(source confidence_hints) clamped to [0,100]
- Sources run concurrently but gated by `asyncio.Semaphore(max_concurrent_sources)`
- `_extract_emails()` filters asset-extension TLDs (png, jpg, css, js…) to avoid false positives

---

## [2026-04-11] — Fixed ruff B017/PT011 violations; CI lint passes cleanly

### What Was Done
- Replaced four `pytest.raises(Exception)` calls in `test_config.py` with `pytest.raises(ValidationError)`
- Added `from pydantic import ValidationError` import
- All 134 tests still pass; `ruff check coldreach tests` reports 0 violations

### Files Changed
| File | Action | Summary |
|------|--------|---------|
| `tests/unit/test_config.py` | Modified | Replaced broad Exception with specific ValidationError in pytest.raises |

### Major Logic / Code Changes
- No logic changes — purely a test quality fix to satisfy ruff B017 (no `pytest.raises(Exception)`) and PT011 (pytest.raises must match specific exception type)

---

## [2026-04-11 01:30] — Phase 1 scaffold + verification layer complete, 134 tests passing

### What Was Done
- Created complete Python project scaffold (pyproject.toml/hatchling, .gitignore, uv-managed venv)
- Implemented full email verification pipeline (syntax → disposable → DNS/MX)
- Wrote 134 unit tests, all passing, 92% coverage
- CLI working: `coldreach verify`, `coldreach find` (stub), `coldreach --version`
- Docker Compose for all 6 backend services
- GitHub Actions CI with Python 3.11/3.12/3.13 matrix + auto PyPI publish on tag
- Pre-commit hooks (ruff + mypy)

### Files Changed
| File | Action | Summary |
|------|--------|---------|
| `pyproject.toml` | Added | Full project config: deps, ruff, mypy, pytest, hatchling build |
| `.gitignore` | Added | Python + Docker + IDE patterns |
| `coldreach/__init__.py` | Added | Version 0.1.0, package metadata |
| `coldreach/config.py` | Added | pydantic-settings, all service URLs, GROQ_API_KEY |
| `coldreach/exceptions.py` | Added | ColdReachError hierarchy |
| `coldreach/core/models.py` | Added | EmailRecord, DomainResult, VerificationStatus, EmailSource Pydantic models |
| `coldreach/verify/_types.py` | Added | CheckResult dataclass with pass_/fail/warn/skip factories |
| `coldreach/verify/syntax.py` | Added | RFC 5322 syntax check via email-validator, lowercase normalisation |
| `coldreach/verify/disposable.py` | Added | 500+ domain blocklist check, lru_cache loaded |
| `coldreach/verify/dns_check.py` | Added | Async MX + A record check via dnspython, priority sorted |
| `coldreach/verify/pipeline.py` | Added | run_basic_pipeline() — chains all 3 checkers, early-stop on FAIL |
| `coldreach/verify/__init__.py` | Added | Public API exports |
| `coldreach/data/disposable_domains.txt` | Added | 500+ disposable email domain blocklist |
| `coldreach/cli.py` | Added | Click CLI: verify command (Rich output + JSON mode), find stub |
| `tests/conftest.py` | Added | Shared fixtures, cache clearing |
| `tests/unit/test_verify_syntax.py` | Added | 19 syntax tests |
| `tests/unit/test_verify_disposable.py` | Added | 23 disposable tests |
| `tests/unit/test_verify_dns.py` | Added | 17 DNS tests (mocked) |
| `tests/unit/test_verify_pipeline.py` | Added | 19 pipeline tests (mocked DNS) |
| `tests/unit/test_core_models.py` | Added | 30 model tests |
| `tests/unit/test_config.py` | Added | 17 config tests |
| `docker-compose.yml` | Added | postgres, redis, searxng, reacher, spiderfoot, firecrawl |
| `.env.example` | Added | All config variables with comments |
| `.pre-commit-config.yaml` | Added | ruff + ruff-format + mypy hooks |
| `.github/workflows/ci.yml` | Added | Test matrix (3.11/3.12/3.13) + lint + PyPI publish |
| `README.md` | Added | Full README: install, usage, comparison table, phase status |

### Major Logic / Code Changes
- Verification pipeline: `run_basic_pipeline()` stops early on first FAIL (syntax fail = skip DNS entirely)
- Score system: baseline 30, +5 not-disposable, +10 MX found, max 100 — honest confidence, not binary
- Email normalization: explicitly lowercase full address (email-validator only lowercases domain by default)
- Async DNS: uses `dns.asyncresolver` natively, no thread pool hacks
- Disposable list: `lru_cache(maxsize=1)` — file read once per process, `frozenset` for O(1) lookup
- `CheckResult` uses `@dataclass(slots=True)` for memory efficiency and clean factory classmethods

### Notes
- IDE shows "Cannot find module" warnings — these are false positives (IDE reads system Python, not .venv)
- `uv` is the package manager. Use `uv run pytest` not `pytest` directly
- Next step: Phase 2 — website crawler source (Crawl4AI), then theHarvester, GitHub, Reddit

---

## [2026-04-11 00:30] — Updated PLAN.md with Holehe/Reacher verification, SearXNG fallback, Docker Compose, TUI, Reddit, SpiderFoot, Firecrawl

### What Was Done
- Added Holehe (120+ platform check) and Reacher (Rust SMTP microservice) to verification pipeline
- Added SearXNG rate limit mitigation: fallback chain SearXNG → DDG Lite → Brave Search API
- Added Firecrawl (self-hosted Docker) alongside Crawl4AI for JS-heavy sites
- Added SpiderFoot (self-hosted Docker) alongside theHarvester for deeper OSINT
- Added Reddit JSON API as free/no-auth data source
- Added full Docker Compose architecture (SearXNG, Firecrawl, SpiderFoot, Reacher, Redis, PostgreSQL)
- Switched primary UI from Streamlit to Textual TUI — Streamlit demoted to optional web UI
- BYOK deferred to Phase 5 — only Groq API kept as optional key for LLM features
- Updated verification pipeline, source reliability table, tech stack, phase plan, project structure

### Files Changed
| File | Action | Summary |
|------|--------|---------|
| `PLAN.md` | Modified | Major updates across verification, sources, Docker Compose, TUI, BYOK strategy |

### Major Logic / Code Changes
- Verification now 6-layer: syntax → DNS → catch-all → Reacher SMTP → Holehe platform → source scoring
- Holehe critical for catch-all domains (SMTP useless there; Holehe checks 120+ platforms independently)
- Reacher runs as Docker microservice — handles Hotmail/Yahoo SMTP edge cases better than smtplib
- SearXNG rate limit explicitly addressed; fallback chain: SearXNG → DDG Lite → Brave Search API
- Reddit JSON: free, no auth, underused source for company/person mentions
- Docker Compose is now the "real install"; pip install coldreach is the CLI/TUI client
- TUI (Textual) is primary UI over Streamlit: SSH-compatible, instant, terminal-native

---

## [2026-04-11 00:00] — Created comprehensive coldreach library plan from research

### What Was Done
- Researched entire open-source ecosystem for lead generation and email finding tools
- Analyzed: theHarvester, Holehe, h8mail, Maigret, Crawl4AI, Firecrawl, CrossLinked, LeadGenPy, Osmedeus
- Analyzed SMTP verification technical limitations (catch-all problem, Gmail/O365 blocking)
- Analyzed email pattern generation (12 common formats), MX/DNS verification pipeline
- Analyzed legal landscape: GDPR, CAN-SPAM, LinkedIn ToS
- Analyzed Chrome extension architecture (Hunter.io, Snov.io, Lusha approaches)
- Created PLAN.md with full architecture, phased roadmap, brutal critique, and honest accuracy targets
- Deleted sampleplan.md (replaced by PLAN.md)

### Files Changed
| File | Action | Summary |
|------|--------|---------|
| `PLAN.md` | Added | Full project plan: architecture, phases, tools, critique, legal compliance |
| `sampleplan.md` | Removed | Replaced by PLAN.md |

### Major Logic / Code Changes
- Defined `coldreach` as the library name (pip installable)
- Defined 4-phase roadmap: Core Library → Enhanced Discovery → Chrome Extension → Outreach Layer
- Architecture: sources/ (crawl, search, github, whois, harvester, commoncrawl) + verify/ (syntax, dns, catchall, smtp) + generate/ (patterns, learner) + enrich/ + outreach/ + storage/ + CLI + FastAPI server + Streamlit dashboard
- Defined confidence scoring algorithm (source-based points system)
- Identified tools to integrate (NOT rebuild): theHarvester, Holehe, Crawl4AI, CrossLinked, python-whois, dnspython
- Defined BYOK model for premium APIs (Hunter, Apollo, Clearbit, Groq, OpenAI)
- Legal compliance layer: opt-out list, GDPR warnings, CAN-SPAM templates, no telemetry

### Removed / Deprecated
- `sampleplan.md` — was a plan for a different project (Fareleaders AI sales agent). Relevant tool references (Crawl4AI, Firecrawl, theHarvester, SearXNG) incorporated into PLAN.md

### Notes
- Accuracy will be lower than Hunter.io/Apollo at launch (honest target: 50-70%) — transparency required
- Chrome extension is Phase 3, not Phase 1 — scope creep risk if started early
- SMTP verification broken for Gmail Workspace + Microsoft 365 catch-all domains — multi-signal scoring is the mitigation
- Biggest differentiator vs paid tools: job board Chrome extension use case (job seekers finding hiring manager contacts)

---

## [2026-04-25 09:42 EDT] — Session close (Cursor)

### What Was Done
- Installed shared session-close skill and automation script for context sync
- Context files were synchronized for cross-agent handoff.
- Graph refresh status: `graphify_update_ok`

### Next
- Use session_close.py at end of every coding session before handoff


## [2026-04-25 10:13 EDT] — Session close (Claude Code)

### What Was Done
- Phase 2 complete: status command + service bar, Docker health checks, Makefile, setup.sh rewrite, Firecrawl separation, crawl4ai/Firecrawl/role-email source integrations, Reacher detection fix, docs updated
- Context files were synchronized for cross-agent handoff.
- Graph refresh status: `graphify_update_ok`

### Next
- Start Phase 3 planning — Chrome extension or FastAPI server for local web UI


## [2026-04-25 12:27 EDT] — Session close (Claude Code)

### What Was Done
- Phase 3A complete: coldreach serve — FastAPI API server with POST /api/find, POST /api/find/stream (SSE), POST /api/verify, GET /api/status, GET/DELETE /api/cache, GET /api/version; PLAN.md updated with phases 3A-6
- Context files were synchronized for cross-agent handoff.
- Graph refresh status: `graphify_update_ok`

### Next
- Phase 3B: Chrome extension — Manifest V3 React popup + Greenhouse/Lever/Indeed content scripts calling localhost:8765


## [2026-04-25 15:33 EDT] — Session close (Claude Code)

### What Was Done
- Phase 3A hardened: 74 API unit tests (100% pass), docs/api-server.md added, cli-reference.md updated with serve command, mkdocs nav updated
- Context files were synchronized for cross-agent handoff.
- Graph refresh status: `graphify_update_ok`

### Next
- Phase 3B: Chrome extension — Manifest V3 React popup calling localhost:8765, content scripts for Greenhouse + Lever + Indeed


## [2026-04-25 15:54 EDT] — Session close (Claude Code)

### What Was Done
- Phase 3B complete: Chrome extension with Manifest V3, React popup (SSE streaming), content scripts for Greenhouse/Lever/Indeed/LinkedIn/Workable, background service worker, docs/chrome-extension.md, npm run build produces clean dist/
- Context files were synchronized for cross-agent handoff.
- Graph refresh status: `graphify_update_ok`

### Next
- Phase 4: Textual TUI — coldreach (no args) launches interactive terminal app reusing diagnostics.py and existing async sources


## [2026-04-25 16:14 EDT] — Session close (Claude Code)

### What Was Done
- Extension UX overhaul: full_scan mode, 0-100% progress bar with start SSE event, right-click context menu, improved Greenhouse DOM detection, richer email table with filter+rescan, API quick=False default, 9 new tests (441 total)
- Context files were synchronized for cross-agent handoff.
- Graph refresh status: `graphify_update_ok`

### Next
- Phase 4: Textual TUI — coldreach with no args launches interactive full-screen terminal app


## [2026-04-26 17:59 EDT] — Session close (Claude Code)

### What Was Done
- Fix SpiderFoot and theHarvester hanging forever: replace -u passive with targeted -m email modules + container timeout binary; remove slow commoncrawl/waybackarchive/thc/threatcrowd from theHarvester; add partial-JSON recovery to SpiderFoot parser
- Context files were synchronized for cross-agent handoff.
- Graph refresh status: `graphify_update_ok`

### Next
- Test full scan against a real domain to verify SpiderFoot finishes in <5 min and theHarvester in <3 min, then proceed to Phase 4 Textual TUI


## [2026-04-26 18:14 EDT] — Session close (Claude Code)

### What Was Done
- Fix theHarvester (docker exec → HTTP REST API at localhost:5050/query) and SpiderFoot (GNU timeout flags → busybox syntax; -u passive -x instead of -m explicit modules); 444 tests pass
- Context files were synchronized for cross-agent handoff.
- Graph refresh status: `graphify_update_ok`

### Next
- Test live: run coldreach find --domain stripe.com with standard mode and verify theharvester + spiderfoot source pills show results


## [2026-04-26 18:38 EDT] — Session close (Claude Code)

### What Was Done
- Fix theHarvester (bing invalid source + source must be list params not comma-joined) and SpiderFoot (-x strict mode excluded email modules; fixed to -m explicit list without -x; fixed JSON parser for Email Address vs EMAILADDR type string)
- Context files were synchronized for cross-agent handoff.
- Graph refresh status: `graphify_update_ok`

### Next
- Run coldreach find --domain stripe.com with standard mode and verify SpiderFoot source pill shows found emails from sfp_pgp module


## [2026-04-26 20:21 EDT] — Session close (Claude Code)

### What Was Done
- Fix SearXNG (wikidata KeyError → disable engine), SpiderFoot (4 fast modules only: sfp_pgp+emailformat+whois+email, 180s limit), background scanning architecture (fast sources immediate, slow sources background task updates cache), theHarvester list-style params already fixed
- Context files were synchronized for cross-agent handoff.
- Graph refresh status: `graphify_update_ok`

### Next
- Run standard scan on a real company domain and verify all fast sources fire in <60s, SpiderFoot completes in <3min as background task


## [2026-05-02 09:40 EDT] — Session close (Claude Code)

### What Was Done
- Job-based pub/sub streaming: SpiderFoot REST API, /api/v2/scan job system with long-lived SSE, extension live email-by-email updates, SearXNG wikidata fix, 443 tests pass
- Context files were synchronized for cross-agent handoff.
- Graph refresh status: `graphify_update_ok`

### Next
- Test full scan on a real domain via extension: verify SpiderFoot emails stream live into popup as PGP keyserver results come in


## [2026-05-02 10:18 EDT] — Session close (Claude Code)

### What Was Done
- Fix extension popup-closes-kills-SSE bug: background SW now runs scan via polling, popup reads from chrome.storage.session; SpiderFoot gets EMAILADDR_COMPROMISED from sfp_citadel; v2 job stores emails for polling; 443 tests pass
- Context files were synchronized for cross-agent handoff.
- Graph refresh status: `graphify_update_ok`

### Next
- Reload extension in Chrome, test snapdeal.com with Standard mode — should see SpiderFoot PGP emails and web crawler emails appearing live in popup even after closing/reopening


## [2026-05-02 10:49 EDT] — Session close (Claude Code)

### What Was Done
- Fix 3 root bugs: (1) web crawler regex rejected emails inside JSON quotes — broadened _EMAIL_RE; (2) role emails never generated in v2 — added generate_role_emails() after fast sources; (3) SearXNG queries returned adult content — improved to '@domain', 'domain email OR contact', 'site:domain'
- Context files were synchronized for cross-agent handoff.
- Graph refresh status: `graphify_update_ok`

### Next
- Run coldreach serve, reload extension, test fareleaders.com — should now show support@fareleaders.com + 9 role pattern emails


## [2026-05-02 11:06 EDT] — Session close (Claude Code)

### What Was Done
- IntelligentSearchSource: Groq+SearXNG+Reddit multi-stage pipeline. Scrapes company site → Groq generates 6 domain-specific queries + 4 subreddits → runs all concurrently through SearXNG + Reddit. Groq key loaded from pydantic-settings. Context uses SearXNG meta-descriptions (works for JS SPAs). Falls back to heuristic queries without Groq.
- Context files were synchronized for cross-agent handoff.
- Graph refresh status: `graphify_update_ok`

### Next
- Test full scan with intelligent_search on snapdeal.com and fareleaders.com — verify Groq-generated queries find emails that generic searches miss


## [2026-05-02 11:44 EDT] — Session close (Claude Code)

### What Was Done
- Phase 3B+ source audit + fixes: SpiderFoot now fetches all 4 email event types (EMAILADDR + COMPROMISED + GENERIC + DELIVERABLE) so sfp_citadel breach data is captured; IntelligentSearch crawls actual SearXNG result URLs for emails (not just snippets); web_crawler expanded to 15 max_pages + careers/press/media/support paths
- Context files were synchronized for cross-agent handoff.
- Graph refresh status: `graphify_update_ok`

### Next
- Test full standard scan on snapdeal.com with all fixes — target 10+ genuine emails. Then audit remaining sources: GitHub (snapdeal has repos?), Reddit (query format), theHarvester (verify /query endpoint actually works with corrected params)


## [2026-05-02 12:22 EDT] — Session close (Claude Code)

### What Was Done
- Phase 3B+ complete: source audit + all fixes. SearchEngine no longer uses '@domain' literal (returns 0). SearchEngine now crawls result URLs. GitHub tries 7 slug variants. SpiderFoot queries all 4 email event types. Combined: 9 genuine emails + 9 patterns for snapdeal.com. 443 tests pass.
- Context files were synchronized for cross-agent handoff.
- Graph refresh status: `graphify_update_ok`

### Next
- Phase 5: Groq draft feature — coldreach find --domain X --name Y --draft → finds email + writes personalized cold email. Also needs a dashboard/UI for managing email templates and outreach campaigns.


## [2026-05-02 12:32 EDT] — Session close (Claude Code)

### What Was Done
- Fix CI ruff format error; add all GitHub community standard files (CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md, 3 issue templates, PR template); update docs/sources.md with IntelligentSearch; add docs/contributing.md
- Context files were synchronized for cross-agent handoff.
- Graph refresh status: `graphify_update_ok`

### Next
- Phase 5: Groq --draft feature + outreach dashboard. User wants: find email + write personalized cold email + UI to manage templates and campaigns.


## [2026-05-02 14:10 EDT] — Session close (Claude Code)

### What Was Done
- Phase 5 complete: coldreach/outreach/ module (context.py, draft.py, templates.py), DSPy ColdEmailSignature for structured Groq output, /api/v2/draft SSE endpoint, --draft CLI flag, coldreach dashboard command, Streamlit 3-tab outreach dashboard, 482 tests pass
- Context files were synchronized for cross-agent handoff.
- Graph refresh status: `graphify_update_ok`

### Next
- Live smoke test: coldreach find --domain stripe.com --name 'Patrick Collison' --draft --sender-name 'Jane' --intent 'explore API partnership'. Then build Chrome extension DraftPanel component.


## [2026-05-02 14:50 EDT] — Session close (Claude Code)

### What Was Done
- Update docs for Phase 5: cli-reference.md (dashboard command, --draft flags), api-server.md (/api/v2/draft endpoint), new docs/outreach.md (full workflow guide A/B/C), mkdocs.yml nav updated. Memory updated to make docs updates mandatory.
- Context files were synchronized for cross-agent handoff.
- Graph refresh status: `graphify_update_ok`

### Next
- Build Chrome extension DraftPanel component (✏️ button per email row, streams /api/v2/draft, shows draft word-by-word, copy button)


## [2026-05-02 15:44 EDT] — Session close (Claude Code)

### What Was Done
- Complete dashboard redesign: professional dark theme with custom CSS tokens, left sidebar navigation (Home/Find/Contacts/Compose/Sent), live SSE scan with source pills + email cards appearing in real time, card grid for contacts with inline Draft/Mark buttons, focused Compose with left/right split, Sent tracker with reply rate
- Context files were synchronized for cross-agent handoff.
- Graph refresh status: `graphify_update_ok`

### Next
- Test dashboard live: coldreach dashboard → scan fareleaders.com → verify emails appear card-by-card → click Draft → verify Groq generates subject+body


## [2026-05-02 16:04 EDT] — Session close (Claude Code)

### What Was Done
- Chrome Extension Draft Button complete: streamDraft() in api.ts (SSE to /api/v2/draft), DraftPanel component (form→generating→done state machine, streams context_ready then draft_complete), ✏️ button on every email row in EmailTable opens inline DraftPanel below the row, Copy full email button, regenerate button, sender name persisted in localStorage
- Context files were synchronized for cross-agent handoff.
- Graph refresh status: `graphify_update_ok`

### Next
- Phase 4: Textual TUI — coldreach with no args launches interactive full-screen terminal app (Find/Verify/Status/Cache screens), reuses diagnostics.py and existing async sources


## [2026-05-02 16:12 EDT] — Session close (Claude Code)

### What Was Done
- Fix DSPy thread-safety crash: replaced dspy.configure() + asyncio.to_thread with single _run_dspy_in_thread() that uses dspy.context(lm=lm) inside the thread — context() scopes the LM to one call, configure() sets global state that breaks across async tasks. Tests updated to patch _run_dspy_in_thread returning (subject,body) tuple.
- Context files were synchronized for cross-agent handoff.
- Graph refresh status: `graphify_update_ok`

### Next
- Phase 4: Textual TUI — coldreach with no args launches interactive terminal app

