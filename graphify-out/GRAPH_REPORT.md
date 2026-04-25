# Graph Report - .  (2026-04-25)

## Corpus Check
- Corpus is ~43,427 words - fits in a single context window. You may not need a graph.

## Summary
- 1070 nodes · 2712 edges · 45 communities detected
- Extraction: 55% EXTRACTED · 45% INFERRED · 0% AMBIGUOUS · INFERRED: 1210 edges (avg confidence: 0.65)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Discovery Sources Core|Discovery Sources Core]]
- [[_COMMUNITY_Data Models and Export|Data Models and Export]]
- [[_COMMUNITY_CLI and Cache Interface|CLI and Cache Interface]]
- [[_COMMUNITY_Email Pattern Generation|Email Pattern Generation]]
- [[_COMMUNITY_Cache Storage Layer|Cache Storage Layer]]
- [[_COMMUNITY_Public Python API|Public Python API]]
- [[_COMMUNITY_Search Engine Source|Search Engine Source]]
- [[_COMMUNITY_Configuration and Settings|Configuration and Settings]]
- [[_COMMUNITY_Disposable Domain Check|Disposable Domain Check]]
- [[_COMMUNITY_Web Crawler Source|Web Crawler Source]]
- [[_COMMUNITY_theHarvester OSINT Source|theHarvester OSINT Source]]
- [[_COMMUNITY_DNSMX Verification|DNS/MX Verification]]
- [[_COMMUNITY_SpiderFoot OSINT Source|SpiderFoot OSINT Source]]
- [[_COMMUNITY_Company Domain Resolver|Company Domain Resolver]]
- [[_COMMUNITY_Email Syntax Validation|Email Syntax Validation]]
- [[_COMMUNITY_Catch-All Domain Detection|Catch-All Domain Detection]]
- [[_COMMUNITY_Reacher SMTP Verification|Reacher SMTP Verification]]
- [[_COMMUNITY_Holehe Platform Check|Holehe Platform Check]]
- [[_COMMUNITY_Exceptions and Errors|Exceptions and Errors]]
- [[_COMMUNITY_Diagnostics and Health|Diagnostics and Health]]
- [[_COMMUNITY_Package Initialization|Package Initialization]]
- [[_COMMUNITY_Role and Pattern Email Sources|Role and Pattern Email Sources]]
- [[_COMMUNITY_Groq API Feature Flag|Groq API Feature Flag]]
- [[_COMMUNITY_SQLite Backend Flag|SQLite Backend Flag]]
- [[_COMMUNITY_Check Status Predicates|Check Status Predicates]]
- [[_COMMUNITY_Check Status Predicates|Check Status Predicates]]
- [[_COMMUNITY_Check Status Predicates|Check Status Predicates]]
- [[_COMMUNITY_Check Status Predicates|Check Status Predicates]]
- [[_COMMUNITY_Check Result Factories|Check Result Factories]]
- [[_COMMUNITY_Check Result Factories|Check Result Factories]]
- [[_COMMUNITY_Check Result Factories|Check Result Factories]]
- [[_COMMUNITY_Check Result Factories|Check Result Factories]]
- [[_COMMUNITY_Email Normalization|Email Normalization]]
- [[_COMMUNITY_Email Domain Property|Email Domain Property]]
- [[_COMMUNITY_Email Local Part Property|Email Local Part Property]]
- [[_COMMUNITY_Source Deduplication|Source Deduplication]]
- [[_COMMUNITY_Primary Source Selection|Primary Source Selection]]
- [[_COMMUNITY_Highest Confidence Email|Highest Confidence Email]]
- [[_COMMUNITY_WHOIS Source|WHOIS Source]]
- [[_COMMUNITY_Reddit Source|Reddit Source]]
- [[_COMMUNITY_Search Engine Source|Search Engine Source]]
- [[_COMMUNITY_Cache CLI Commands|Cache CLI Commands]]
- [[_COMMUNITY_CLI Exit Codes|CLI Exit Codes]]
- [[_COMMUNITY_Dev Environment Setup|Dev Environment Setup]]
- [[_COMMUNITY_Project Roadmap|Project Roadmap]]

## God Nodes (most connected - your core abstractions)
1. `EmailSource` - 114 edges
2. `SourceResult` - 84 edges
3. `BaseSource` - 74 edges
4. `DomainResult` - 68 edges
5. `EmailRecord` - 57 edges
6. `CacheStore` - 51 edges
7. `CheckStatus` - 48 edges
8. `CheckResult` - 43 edges
9. `HarvesterSource` - 42 edges
10. `SpiderFootSource` - 40 edges

## Surprising Connections (you probably didn't know these)
- `FirecrawlSource: Opt-in Sitemap Discovery + Multi-page Scraping` --semantically_similar_to--> `WebCrawlerSource: Homepage + Contact/Team/About Pages`  [INFERRED] [semantically similar]
  PROGRESS.md → docs/sources.md
- `Crawl4AISource: Playwright JS Rendering for SPAs` --semantically_similar_to--> `WebCrawlerSource: Homepage + Contact/Team/About Pages`  [INFERRED] [semantically similar]
  PROGRESS.md → docs/sources.md
- `No API Keys Required (Groq Optional)` --semantically_similar_to--> `Company Resolver: Clearbit Autocomplete + DDG Fallback (No Keys)`  [INFERRED] [semantically similar]
  README.md → PROGRESS.md
- `Role Emails: Always-On info/sales/contact Candidates` --semantically_similar_to--> `Pattern Generator Source: Name + Format Inference`  [INFERRED] [semantically similar]
  PROGRESS.md → docs/sources.md
- `HTML Entity Prefix Filter: Removes JS Unicode Escape Artifacts` --references--> `WebCrawlerSource: Homepage + Contact/Team/About Pages`  [INFERRED]
  PROGRESS.md → docs/sources.md

## Hyperedges (group relationships)
- **All Discovery Sources Running Concurrently** — sources_website_crawler, sources_whois_source, sources_github_source, sources_reddit_source, sources_search_engine_source, sources_harvester_source, sources_spiderfoot_source [EXTRACTED 1.00]
- **Verification Pipeline: 5 Sequential Checks** — how_it_works_syntax_check, how_it_works_disposable_check, how_it_works_dns_mx_check, how_it_works_reacher_smtp, how_it_works_holehe_check [EXTRACTED 1.00]
- **Core Pydantic Data Models Flowing Through Pipeline** — api_models_domain_result, api_models_email_record, api_models_source_record [EXTRACTED 1.00]

## Communities

### Community 0 - "Discovery Sources Core"
Cohesion: 0.04
Nodes (93): ABC, BaseSource, fetch(), Abstract base class for all ColdReach email discovery sources.  Every source fol, Safe wrapper around :meth:`fetch` — never raises.          Returns the results l, A single email address found by a source.      Attributes     ----------     ema, Execution summary for one source run., Abstract base for all email discovery sources.      Subclasses must implement :m (+85 more)

### Community 1 - "Data Models and Export"
Cohesion: 0.05
Nodes (38): BaseModel, best_email(), domain(), DomainResult, EmailRecord, local_part(), normalise_domain(), normalise_email() (+30 more)

### Community 2 - "CLI and Cache Interface"
Cohesion: 0.05
Nodes (74): _banner(), cache(), cache_clear(), cache_list(), cache_stats(), _configure_logging(), _domain_result_to_dict(), find() (+66 more)

### Community 3 - "Email Pattern Generation"
Cohesion: 0.05
Nodes (28): learn_format(), Domain email format learner.  Infers a company's email format from confirmed add, Return the most likely email format_name for *domain*.      Analyses the local p, Generate targeted email candidates for *full_name* at *domain*.      When a doma, targeted_patterns(), _clean_name_part(), EmailPattern, generate_patterns() (+20 more)

### Community 4 - "Cache Storage Layer"
Cohesion: 0.08
Nodes (20): CacheStore, Local result cache for ColdReach domain scans.  Two-layer cache:   1. SQLite  —, Store *result* for *domain* in all available cache layers., Delete cached entries.          Parameters         ----------         domain:, Return all cached domains as (domain, cached_at, is_expired) tuples., Return basic cache statistics., SQLite-backed domain result cache with optional Redis layer.      Parameters, Return a cached DomainResult for *domain*, or ``None`` on miss/expiry. (+12 more)

### Community 5 - "Public Python API"
Cohesion: 0.04
Nodes (58): Format Learner: Infers Email Format from Known Emails, generate_patterns(): Email Address Generation, find_emails(config: FinderConfig) Async Entry Point, Python Public API (importable modules), run_basic_pipeline() Async Entry Point, DomainResult: Top-Level Result Pydantic Model, EmailRecord: Per-Email Pydantic Model with Confidence, SourceRecord: Per-Source Discovery Result (+50 more)

### Community 6 - "Search Engine Source"
Cohesion: 0.08
Nodes (31): _build_queries(), _extract_domain_emails(), _query_brave(), _query_ddg_lite(), _query_searxng(), Search engine source — queries SearXNG (self-hosted) for domain email mentions., _make_commit(), _mock_json_response() (+23 more)

### Community 7 - "Configuration and Settings"
Cohesion: 0.07
Nodes (27): BaseSettings, get_settings(), has_groq(), ColdReach configuration via pydantic-settings.  All settings are read from envir, Return the singleton Settings instance.      Results are cached after the first, All runtime configuration for ColdReach.      Every field can be overridden by a, Settings, using_sqlite() (+19 more)

### Community 8 - "Disposable Domain Check"
Cohesion: 0.07
Nodes (14): check_disposable(), is_disposable(), _load_domains(), Disposable / throwaway email domain detection.  Checks whether the domain part o, Parse and cache the bundled disposable domain blocklist.      Returns     ------, Return True if *email* uses a known disposable / throwaway domain.      Paramete, Pipeline checker: fail if email uses a disposable domain.      Parameters     --, Unit tests for coldreach.verify.disposable  All tests are pure CPU — the blockli (+6 more)

### Community 9 - "Web Crawler Source"
Cohesion: 0.09
Nodes (17): _classify_path(), _mock_response(), Unit tests for coldreach.sources.web_crawler  All HTTP calls are mocked — no rea, test_contact_page_gets_correct_source_type(), test_deduplicates_across_pages(), test_finds_email_on_homepage(), test_returns_empty_on_http_error(), test_source_name_is_web_crawler() (+9 more)

### Community 10 - "theHarvester OSINT Source"
Cohesion: 0.11
Nodes (17): HarvesterSource, theHarvester source — CLI runner via docker exec.  Runs theHarvester inside the, _json_file(), _make_proc(), Unit tests for coldreach.sources.harvester  docker exec / subprocess calls are m, test_kills_process_on_timeout(), test_returns_emails_on_success(), test_returns_empty_on_nonzero_exit() (+9 more)

### Community 11 - "DNS/MX Verification"
Cohesion: 0.13
Nodes (33): check_dns(), domain_exists(), get_mx_records(), Async DNS / MX record checker.  Resolves MX records for an email's domain to con, Pipeline checker: verify the email's domain has a valid MX record.      Scoring, Resolve MX records for *domain*, sorted by priority (lowest first).      Paramet, Return True if *domain* resolves to at least one A or AAAA record.      Used as, _make_mx_answer() (+25 more)

### Community 12 - "SpiderFoot OSINT Source"
Cohesion: 0.15
Nodes (15): SpiderFoot source — CLI runner via docker exec.  Runs sf.py inside the ``coldrea, SpiderFootSource, _json_rows(), _make_proc(), Unit tests for coldreach.sources.spiderfoot  docker exec / subprocess calls are, test_kills_process_on_timeout(), test_returns_emails_on_success(), test_returns_empty_on_nonzero_exit() (+7 more)

### Community 13 - "Company Domain Resolver"
Cohesion: 0.12
Nodes (24): _extract_domain_from_ddg_html(), Company name → primary domain resolver.  Strategy (tried in order, stops on firs, Query Clearbit Autocomplete for the company domain., Search DuckDuckGo Lite and extract domain from first result URL., Parse DuckDuckGo Lite HTML and return the domain of the first organic result., Resolve a company name to its primary domain.      Parameters     ----------, resolve_domain(), _try_clearbit() (+16 more)

### Community 14 - "Email Syntax Validation"
Cohesion: 0.1
Nodes (10): check_syntax(), Email syntax validation (RFC 5321 / 5322).  Uses the ``email-validator`` library, Validate an email address against RFC 5322 syntax rules.      Does **not** check, Unit tests for coldreach.verify.syntax.check_syntax  All tests are pure CPU — no, Cases that should PASS syntax validation., Cases that should FAIL syntax validation., Edge cases and unusual but technically valid inputs., TestCheckSyntaxEdgeCases (+2 more)

### Community 15 - "Catch-All Domain Detection"
Cohesion: 0.14
Nodes (25): check_catchall(), clear_cache(), is_catch_all(), _probe_via_reacher(), _random_local(), Catch-all domain detection.  A "catch-all" mail server accepts RCPT TO for ANY a, Return True/False/None for catch-all status.      Convenience wrapper around :fu, Send a probe to Reacher. Returns True=catch-all, False=not, None=unknown. (+17 more)

### Community 16 - "Reacher SMTP Verification"
Cohesion: 0.17
Nodes (15): check_reacher(), _parse_reacher_response(), Reacher SMTP verification client.  Reacher (https://reacher.email) is a self-hos, Verify *email* via the Reacher SMTP microservice.      Parameters     ----------, Interpret the Reacher JSON response into a CheckResult., _mock_http_response(), Unit tests for coldreach.verify.reacher  Reacher HTTP calls are mocked — no real, _reacher_data() (+7 more)

### Community 17 - "Holehe Platform Check"
Cohesion: 0.24
Nodes (17): check_holehe(), Holehe platform-presence check.  Uses the holehe library (github.com/megadose/ho, Check if *email* is registered on public platforms via holehe.      Parameters, _make_modules(), _patch_holehe_core(), Unit tests for coldreach.verify.holehe  holehe HTTP calls are mocked — no real n, Build fake holehe module coroutine functions that append *results* to out., Patch holehe.core so check_holehe uses our fake modules. (+9 more)

### Community 18 - "Exceptions and Errors"
Cohesion: 0.19
Nodes (14): Exception, ColdReachError, ConfigError, RateLimitError, ColdReach custom exceptions.  Hierarchy --------- ColdReachError ├── ConfigError, Base exception for all ColdReach errors., Raised when configuration is invalid or missing., Raised when a data source fails to return results. (+6 more)

### Community 19 - "Diagnostics and Health"
Cohesion: 0.21
Nodes (16): _check_package(), DiagnosticsReport, PackageResult, packages_installed(), _ping(), quick_service_check(), ColdReach diagnostics — service availability and package install checks.  Used b, Run all checks concurrently and return a DiagnosticsReport.      Parameters (+8 more)

### Community 20 - "Package Initialization"
Cohesion: 0.12
Nodes (1): ColdReach email discovery sources.

### Community 21 - "Role and Pattern Email Sources"
Cohesion: 1.0
Nodes (2): Role Emails: Always-On info/sales/contact Candidates, Pattern Generator Source: Name + Format Inference

### Community 22 - "Groq API Feature Flag"
Cohesion: 1.0
Nodes (1): True if a Groq API key is configured.

### Community 23 - "SQLite Backend Flag"
Cohesion: 1.0
Nodes (1): True if the database backend is SQLite (no Docker needed).

### Community 24 - "Check Status Predicates"
Cohesion: 1.0
Nodes (1): True if status is PASS.

### Community 25 - "Check Status Predicates"
Cohesion: 1.0
Nodes (1): True if status is FAIL.

### Community 26 - "Check Status Predicates"
Cohesion: 1.0
Nodes (1): True if status is WARN.

### Community 27 - "Check Status Predicates"
Cohesion: 1.0
Nodes (1): True if status is SKIP.

### Community 28 - "Check Result Factories"
Cohesion: 1.0
Nodes (1): Create a passing result.

### Community 29 - "Check Result Factories"
Cohesion: 1.0
Nodes (1): Create a failing result.

### Community 30 - "Check Result Factories"
Cohesion: 1.0
Nodes (1): Create a warning result.

### Community 31 - "Check Result Factories"
Cohesion: 1.0
Nodes (1): Create a skipped result.

### Community 32 - "Email Normalization"
Cohesion: 1.0
Nodes (1): Lowercase and strip whitespace.

### Community 33 - "Email Domain Property"
Cohesion: 1.0
Nodes (1): The domain part of the email address.

### Community 34 - "Email Local Part Property"
Cohesion: 1.0
Nodes (1): The local (username) part of the email address.

### Community 35 - "Source Deduplication"
Cohesion: 1.0
Nodes (1): Deduplicated list of source identifiers that found this email.

### Community 36 - "Primary Source Selection"
Cohesion: 1.0
Nodes (1): The highest-priority source that found this email.

### Community 37 - "Highest Confidence Email"
Cohesion: 1.0
Nodes (1): Return the email with the highest confidence score.

### Community 42 - "WHOIS Source"
Cohesion: 1.0
Nodes (1): WhoisSource: Domain Registrant Contact Email

### Community 43 - "Reddit Source"
Cohesion: 1.0
Nodes (1): RedditSource: Post Body/Comment Email Extraction

### Community 44 - "Search Engine Source"
Cohesion: 1.0
Nodes (1): SearchEngineSource: SearXNG → DDG → Brave Fallback Chain

### Community 45 - "Cache CLI Commands"
Cohesion: 1.0
Nodes (1): CLI: coldreach cache list/stats/clear

### Community 46 - "CLI Exit Codes"
Cohesion: 1.0
Nodes (1): CLI Exit Codes: 0=pass, 1=fail, 2=usage error

### Community 47 - "Dev Environment Setup"
Cohesion: 1.0
Nodes (1): Dev Install: uv sync --all-extras --dev

### Community 48 - "Project Roadmap"
Cohesion: 1.0
Nodes (1): Project PLAN.md: Feature Roadmap and Architecture Notes

## Knowledge Gaps
- **96 isolated node(s):** `All runtime configuration for ColdReach.      Every field can be overridden by a`, `True if a Groq API key is configured.`, `True if the database backend is SQLite (no Docker needed).`, `Return the singleton Settings instance.      Results are cached after the first`, `Base exception for all ColdReach errors.` (+91 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Package Initialization`** (17 nodes): `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `ColdReach email discovery sources.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Role and Pattern Email Sources`** (2 nodes): `Role Emails: Always-On info/sales/contact Candidates`, `Pattern Generator Source: Name + Format Inference`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Groq API Feature Flag`** (1 nodes): `True if a Groq API key is configured.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `SQLite Backend Flag`** (1 nodes): `True if the database backend is SQLite (no Docker needed).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Check Status Predicates`** (1 nodes): `True if status is PASS.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Check Status Predicates`** (1 nodes): `True if status is FAIL.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Check Status Predicates`** (1 nodes): `True if status is WARN.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Check Status Predicates`** (1 nodes): `True if status is SKIP.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Check Result Factories`** (1 nodes): `Create a passing result.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Check Result Factories`** (1 nodes): `Create a failing result.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Check Result Factories`** (1 nodes): `Create a warning result.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Check Result Factories`** (1 nodes): `Create a skipped result.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Email Normalization`** (1 nodes): `Lowercase and strip whitespace.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Email Domain Property`** (1 nodes): `The domain part of the email address.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Email Local Part Property`** (1 nodes): `The local (username) part of the email address.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Source Deduplication`** (1 nodes): `Deduplicated list of source identifiers that found this email.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Primary Source Selection`** (1 nodes): `The highest-priority source that found this email.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Highest Confidence Email`** (1 nodes): `Return the email with the highest confidence score.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `WHOIS Source`** (1 nodes): `WhoisSource: Domain Registrant Contact Email`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Reddit Source`** (1 nodes): `RedditSource: Post Body/Comment Email Extraction`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Search Engine Source`** (1 nodes): `SearchEngineSource: SearXNG → DDG → Brave Fallback Chain`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Cache CLI Commands`** (1 nodes): `CLI: coldreach cache list/stats/clear`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `CLI Exit Codes`** (1 nodes): `CLI Exit Codes: 0=pass, 1=fail, 2=usage error`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Dev Environment Setup`** (1 nodes): `Dev Install: uv sync --all-extras --dev`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Project Roadmap`** (1 nodes): `Project PLAN.md: Feature Roadmap and Architecture Notes`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `find_emails()` connect `Discovery Sources Core` to `Data Models and Export`, `CLI and Cache Interface`, `Email Pattern Generation`, `Cache Storage Layer`, `Web Crawler Source`, `theHarvester OSINT Source`, `SpiderFoot OSINT Source`?**
  _High betweenness centrality (0.146) - this node is a cross-community bridge._
- **Why does `run_basic_pipeline()` connect `CLI and Cache Interface` to `Discovery Sources Core`, `Cache Storage Layer`, `Disposable Domain Check`, `DNS/MX Verification`, `Email Syntax Validation`, `Reacher SMTP Verification`, `Holehe Platform Check`?**
  _High betweenness centrality (0.127) - this node is a cross-community bridge._
- **Why does `EmailSource` connect `Discovery Sources Core` to `Data Models and Export`, `CLI and Cache Interface`, `Search Engine Source`, `Web Crawler Source`, `theHarvester OSINT Source`, `SpiderFoot OSINT Source`?**
  _High betweenness centrality (0.119) - this node is a cross-community bridge._
- **Are the 110 inferred relationships involving `EmailSource` (e.g. with `FinderConfig` and `find_emails() — the main orchestrator.  Runs all configured sources concurrently`) actually correct?**
  _`EmailSource` has 110 INFERRED edges - model-reasoned connections that need verification._
- **Are the 81 inferred relationships involving `SourceResult` (e.g. with `FinderConfig` and `find_emails() — the main orchestrator.  Runs all configured sources concurrently`) actually correct?**
  _`SourceResult` has 81 INFERRED edges - model-reasoned connections that need verification._
- **Are the 68 inferred relationships involving `BaseSource` (e.g. with `FinderConfig` and `find_emails() — the main orchestrator.  Runs all configured sources concurrently`) actually correct?**
  _`BaseSource` has 68 INFERRED edges - model-reasoned connections that need verification._
- **Are the 60 inferred relationships involving `DomainResult` (e.g. with `ColdReach CLI — entry point for all terminal commands.  Commands --------     co` and `ColdReach — open-source email finder and lead discovery tool.      \b     Free a`) actually correct?**
  _`DomainResult` has 60 INFERRED edges - model-reasoned connections that need verification._