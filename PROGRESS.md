# Project Progress Log

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
