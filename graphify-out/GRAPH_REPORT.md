# Graph Report - coldemailer  (2026-04-25)

## Corpus Check
- 62 files · ~45,497 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1021 nodes · 2355 edges · 44 communities detected
- Extraction: 49% EXTRACTED · 51% INFERRED · 0% AMBIGUOUS · INFERRED: 1210 edges (avg confidence: 0.65)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]

## God Nodes (most connected - your core abstractions)
1. `EmailSource` - 113 edges
2. `SourceResult` - 83 edges
3. `BaseSource` - 73 edges
4. `DomainResult` - 67 edges
5. `EmailRecord` - 56 edges
6. `CacheStore` - 50 edges
7. `CheckStatus` - 47 edges
8. `CheckResult` - 42 edges
9. `HarvesterSource` - 41 edges
10. `SpiderFootSource` - 39 edges

## Surprising Connections (you probably didn't know these)
- `WebCrawlerSource: Homepage + Contact/Team/About Pages` --semantically_similar_to--> `FirecrawlSource: Opt-in Sitemap Discovery + Multi-page Scraping`  [INFERRED] [semantically similar]
  docs/sources.md → PROGRESS.md
- `WebCrawlerSource: Homepage + Contact/Team/About Pages` --semantically_similar_to--> `Crawl4AISource: Playwright JS Rendering for SPAs`  [INFERRED] [semantically similar]
  docs/sources.md → PROGRESS.md
- `CheckStatus` --uses--> `TestCheckHolehe`  [INFERRED]
  coldreach/verify/_types.py → tests/unit/test_verify_holehe.py
- `CheckStatus` --uses--> `Unit tests for coldreach.verify.holehe  holehe HTTP calls are mocked — no real n`  [INFERRED]
  coldreach/verify/_types.py → tests/unit/test_verify_holehe.py
- `CheckStatus` --uses--> `Build fake holehe module coroutine functions that append *results* to out.`  [INFERRED]
  coldreach/verify/_types.py → tests/unit/test_verify_holehe.py

## Hyperedges (group relationships)
- **All Discovery Sources Running Concurrently** — sources_website_crawler, sources_whois_source, sources_github_source, sources_reddit_source, sources_search_engine_source, sources_harvester_source, sources_spiderfoot_source [EXTRACTED 1.00]
- **Verification Pipeline: 5 Sequential Checks** — how_it_works_syntax_check, how_it_works_disposable_check, how_it_works_dns_mx_check, how_it_works_reacher_smtp, how_it_works_holehe_check [EXTRACTED 1.00]
- **Core Pydantic Data Models Flowing Through Pipeline** — api_models_domain_result, api_models_email_record, api_models_source_record [EXTRACTED 1.00]

## Communities

### Community 0 - "Community 0"
Cohesion: 0.04
Nodes (101): ABC, BaseSource, fetch(), Abstract base class for all ColdReach email discovery sources.  Every source fol, Safe wrapper around :meth:`fetch` — never raises.          Returns the results l, A single email address found by a source.      Attributes     ----------     ema, Execution summary for one source run., Abstract base for all email discovery sources.      Subclasses must implement :m (+93 more)

### Community 1 - "Community 1"
Cohesion: 0.04
Nodes (48): BaseModel, CacheStore, Local result cache for ColdReach domain scans.  Two-layer cache:   1. SQLite  —, Store *result* for *domain* in all available cache layers., Delete cached entries.          Parameters         ----------         domain:, Return all cached domains as (domain, cached_at, is_expired) tuples., Return basic cache statistics., SQLite-backed domain result cache with optional Redis layer.      Parameters (+40 more)

### Community 2 - "Community 2"
Cohesion: 0.04
Nodes (81): check_catchall(), clear_cache(), is_catch_all(), _probe_via_reacher(), _random_local(), Catch-all domain detection.  A "catch-all" mail server accepts RCPT TO for ANY a, Return True/False/None for catch-all status.      Convenience wrapper around :fu, Send a probe to Reacher. Returns True=catch-all, False=not, None=unknown. (+73 more)

### Community 3 - "Community 3"
Cohesion: 0.06
Nodes (30): HarvesterSource, SpiderFootSource, _json_file(), _make_proc(), Unit tests for coldreach.sources.harvester  docker exec / subprocess calls are m, test_kills_process_on_timeout(), test_returns_emails_on_success(), test_returns_empty_on_nonzero_exit() (+22 more)

### Community 4 - "Community 4"
Cohesion: 0.05
Nodes (28): learn_format(), Domain email format learner.  Infers a company's email format from confirmed add, Return the most likely email format_name for *domain*.      Analyses the local p, Generate targeted email candidates for *full_name* at *domain*.      When a doma, targeted_patterns(), _clean_name_part(), EmailPattern, generate_patterns() (+20 more)

### Community 5 - "Community 5"
Cohesion: 0.05
Nodes (45): Return a cached DomainResult for *domain*, or ``None`` on miss/expiry., find(), Find email addresses for a domain or company.      \b     Speed presets:       -, Print a styled email discovery report to stdout., _render_find(), _extract_domain_from_ddg_html(), Company name → primary domain resolver.  Strategy (tried in order, stops on firs, Query Clearbit Autocomplete for the company domain. (+37 more)

### Community 6 - "Community 6"
Cohesion: 0.04
Nodes (58): Format Learner: Infers Email Format from Known Emails, generate_patterns(): Email Address Generation, find_emails(config: FinderConfig) Async Entry Point, Python Public API (importable modules), run_basic_pipeline() Async Entry Point, DomainResult: Top-Level Result Pydantic Model, EmailRecord: Per-Email Pydantic Model with Confidence, SourceRecord: Per-Source Discovery Result (+50 more)

### Community 7 - "Community 7"
Cohesion: 0.07
Nodes (14): check_disposable(), is_disposable(), _load_domains(), Disposable / throwaway email domain detection.  Checks whether the domain part o, Parse and cache the bundled disposable domain blocklist.      Returns     ------, Return True if *email* uses a known disposable / throwaway domain.      Paramete, Pipeline checker: fail if email uses a disposable domain.      Parameters     --, Unit tests for coldreach.verify.disposable  All tests are pure CPU — the blockli (+6 more)

### Community 8 - "Community 8"
Cohesion: 0.06
Nodes (16): BaseSettings, get_settings(), ColdReach configuration via pydantic-settings.  All settings are read from envir, Return the singleton Settings instance.      Results are cached after the first, All runtime configuration for ColdReach.      Every field can be overridden by a, Settings, _clear_settings_cache(), Shared pytest fixtures for all test modules. (+8 more)

### Community 9 - "Community 9"
Cohesion: 0.1
Nodes (26): _extract_domain_emails(), RedditSource, _make_commit(), _mock_json_response(), test_deduplicates_same_email_across_commits(), test_filters_emails_from_other_domains(), test_filters_out_noreply_emails(), test_finds_domain_email_in_commits() (+18 more)

### Community 10 - "Community 10"
Cohesion: 0.11
Nodes (15): _build_queries(), _extract_domain_emails(), _query_brave(), _query_ddg_lite(), _query_searxng(), SearchEngineSource, TestExtractDomainEmails, Unit tests for coldreach.sources.search_engine  All HTTP calls are mocked. (+7 more)

### Community 11 - "Community 11"
Cohesion: 0.11
Nodes (18): check_reacher(), _parse_reacher_response(), Reacher SMTP verification client.  Reacher (https://reacher.email) is a self-hos, Verify *email* via the Reacher SMTP microservice.      Parameters     ----------, Interpret the Reacher JSON response into a CheckResult., _mock_http_response(), Unit tests for coldreach.verify.reacher  Reacher HTTP calls are mocked — no real, _reacher_data() (+10 more)

### Community 12 - "Community 12"
Cohesion: 0.1
Nodes (10): check_syntax(), Email syntax validation (RFC 5321 / 5322).  Uses the ``email-validator`` library, Validate an email address against RFC 5322 syntax rules.      Does **not** check, Unit tests for coldreach.verify.syntax.check_syntax  All tests are pure CPU — no, Cases that should PASS syntax validation., Cases that should FAIL syntax validation., Edge cases and unusual but technically valid inputs., TestCheckSyntaxEdgeCases (+2 more)

### Community 13 - "Community 13"
Cohesion: 0.13
Nodes (27): check_dns(), domain_exists(), get_mx_records(), Async DNS / MX record checker.  Resolves MX records for an email's domain to con, Pipeline checker: verify the email's domain has a valid MX record.      Scoring, Resolve MX records for *domain*, sorted by priority (lowest first).      Paramet, Return True if *domain* resolves to at least one A or AAAA record.      Used as, _make_mx_answer() (+19 more)

### Community 14 - "Community 14"
Cohesion: 0.17
Nodes (7): _make_result(), Unit tests for coldreach.export.writer  No network calls — all I/O uses tmp_path, TestExportCSV, TestExportJSON, TestExportValidation, export_results(), Write *result* to *output_path* in CSV or JSON format.      Format is determined

### Community 15 - "Community 15"
Cohesion: 0.22
Nodes (17): check_holehe(), Holehe platform-presence check.  Uses the holehe library (github.com/megadose/ho, Check if *email* is registered on public platforms via holehe.      Parameters, _make_modules(), _patch_holehe_core(), Unit tests for coldreach.verify.holehe  holehe HTTP calls are mocked — no real n, Build fake holehe module coroutine functions that append *results* to out., Patch holehe.core so check_holehe uses our fake modules. (+9 more)

### Community 16 - "Community 16"
Cohesion: 0.16
Nodes (14): Exception, ColdReachError, ConfigError, RateLimitError, ColdReach custom exceptions.  Hierarchy --------- ColdReachError ├── ConfigError, Base exception for all ColdReach errors., Raised when configuration is invalid or missing., Raised when a data source fails to return results. (+6 more)

### Community 17 - "Community 17"
Cohesion: 0.36
Nodes (11): append_decisions(), append_handoff(), append_progress(), ensure_context_files(), git_branch(), main(), now_stamp(), parse_args() (+3 more)

### Community 18 - "Community 18"
Cohesion: 0.33
Nodes (2): TestExtractEmails, _extract_emails()

### Community 19 - "Community 19"
Cohesion: 0.39
Nodes (2): _classify_path(), TestClassifyPath

### Community 20 - "Community 20"
Cohesion: 1.0
Nodes (2): Role Emails: Always-On info/sales/contact Candidates, Pattern Generator Source: Name + Format Inference

### Community 21 - "Community 21"
Cohesion: 1.0
Nodes (1): True if a Groq API key is configured.

### Community 22 - "Community 22"
Cohesion: 1.0
Nodes (1): True if the database backend is SQLite (no Docker needed).

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (1): True if status is PASS.

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): True if status is FAIL.

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): True if status is WARN.

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): True if status is SKIP.

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Create a passing result.

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Create a failing result.

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): Create a warning result.

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): Create a skipped result.

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (1): Lowercase and strip whitespace.

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (1): The domain part of the email address.

### Community 33 - "Community 33"
Cohesion: 1.0
Nodes (1): The local (username) part of the email address.

### Community 34 - "Community 34"
Cohesion: 1.0
Nodes (1): Deduplicated list of source identifiers that found this email.

### Community 35 - "Community 35"
Cohesion: 1.0
Nodes (1): The highest-priority source that found this email.

### Community 36 - "Community 36"
Cohesion: 1.0
Nodes (1): Return the email with the highest confidence score.

### Community 39 - "Community 39"
Cohesion: 1.0
Nodes (1): WhoisSource: Domain Registrant Contact Email

### Community 40 - "Community 40"
Cohesion: 1.0
Nodes (1): RedditSource: Post Body/Comment Email Extraction

### Community 41 - "Community 41"
Cohesion: 1.0
Nodes (1): SearchEngineSource: SearXNG → DDG → Brave Fallback Chain

### Community 42 - "Community 42"
Cohesion: 1.0
Nodes (1): CLI: coldreach cache list/stats/clear

### Community 43 - "Community 43"
Cohesion: 1.0
Nodes (1): CLI Exit Codes: 0=pass, 1=fail, 2=usage error

### Community 44 - "Community 44"
Cohesion: 1.0
Nodes (1): Dev Install: uv sync --all-extras --dev

### Community 45 - "Community 45"
Cohesion: 1.0
Nodes (1): Project PLAN.md: Feature Roadmap and Architecture Notes

## Knowledge Gaps
- **109 isolated node(s):** `ColdReach configuration via pydantic-settings.  All settings are read from envir`, `All runtime configuration for ColdReach.      Every field can be overridden by a`, `True if a Groq API key is configured.`, `True if the database backend is SQLite (no Docker needed).`, `Return the singleton Settings instance.      Results are cached after the first` (+104 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 18`** (11 nodes): `TestExtractEmails`, `.test_deduplicates_emails()`, `.test_filters_other_domains()`, `.test_ignores_image_extensions()`, `.test_mailto_link()`, `.test_normalises_to_lowercase()`, `.test_obfuscated_at_bracket()`, `.test_obfuscated_at_paren()`, `.test_plain_email_in_text()`, `.test_subdomain_email_included()`, `_extract_emails()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 19`** (9 nodes): `_classify_path()`, `TestClassifyPath`, `.test_about_path()`, `.test_case_insensitive()`, `.test_contact_path()`, `.test_contact_us_path()`, `.test_people_path()`, `.test_team_path()`, `.test_unknown_path_is_generic()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 20`** (2 nodes): `Role Emails: Always-On info/sales/contact Candidates`, `Pattern Generator Source: Name + Format Inference`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (1 nodes): `True if a Groq API key is configured.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (1 nodes): `True if the database backend is SQLite (no Docker needed).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (1 nodes): `True if status is PASS.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (1 nodes): `True if status is FAIL.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `True if status is WARN.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `True if status is SKIP.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `Create a passing result.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `Create a failing result.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `Create a warning result.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `Create a skipped result.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `Lowercase and strip whitespace.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `The domain part of the email address.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (1 nodes): `The local (username) part of the email address.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (1 nodes): `Deduplicated list of source identifiers that found this email.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (1 nodes): `The highest-priority source that found this email.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 36`** (1 nodes): `Return the email with the highest confidence score.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 39`** (1 nodes): `WhoisSource: Domain Registrant Contact Email`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 40`** (1 nodes): `RedditSource: Post Body/Comment Email Extraction`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (1 nodes): `SearchEngineSource: SearXNG → DDG → Brave Fallback Chain`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (1 nodes): `CLI: coldreach cache list/stats/clear`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 43`** (1 nodes): `CLI Exit Codes: 0=pass, 1=fail, 2=usage error`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 44`** (1 nodes): `Dev Install: uv sync --all-extras --dev`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 45`** (1 nodes): `Project PLAN.md: Feature Roadmap and Architecture Notes`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `find_emails()` connect `Community 0` to `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 9`, `Community 10`?**
  _High betweenness centrality (0.135) - this node is a cross-community bridge._
- **Why does `run_basic_pipeline()` connect `Community 2` to `Community 0`, `Community 5`, `Community 7`, `Community 11`, `Community 12`, `Community 13`, `Community 15`?**
  _High betweenness centrality (0.111) - this node is a cross-community bridge._
- **Why does `CacheStore` connect `Community 1` to `Community 0`, `Community 2`, `Community 5`?**
  _High betweenness centrality (0.106) - this node is a cross-community bridge._
- **Are the 110 inferred relationships involving `EmailSource` (e.g. with `FinderConfig` and `find_emails() — the main orchestrator.  Runs all configured sources concurrently`) actually correct?**
  _`EmailSource` has 110 INFERRED edges - model-reasoned connections that need verification._
- **Are the 81 inferred relationships involving `SourceResult` (e.g. with `FinderConfig` and `find_emails() — the main orchestrator.  Runs all configured sources concurrently`) actually correct?**
  _`SourceResult` has 81 INFERRED edges - model-reasoned connections that need verification._
- **Are the 68 inferred relationships involving `BaseSource` (e.g. with `FinderConfig` and `find_emails() — the main orchestrator.  Runs all configured sources concurrently`) actually correct?**
  _`BaseSource` has 68 INFERRED edges - model-reasoned connections that need verification._
- **Are the 60 inferred relationships involving `DomainResult` (e.g. with `ColdReach CLI — entry point for all terminal commands.  Commands --------     co` and `ColdReach — open-source email finder and lead discovery tool.      \b     Free a`) actually correct?**
  _`DomainResult` has 60 INFERRED edges - model-reasoned connections that need verification._