# Graph Report - coldemailer  (2026-05-02)

## Corpus Check
- 86 files · ~66,869 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1401 nodes · 5092 edges · 51 communities detected
- Extraction: 28% EXTRACTED · 72% INFERRED · 0% AMBIGUOUS · INFERRED: 3643 edges (avg confidence: 0.57)
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
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]

## God Nodes (most connected - your core abstractions)
1. `SourceResult` - 263 edges
2. `BaseSource` - 252 edges
3. `DomainResult` - 213 edges
4. `EmailSource` - 200 edges
5. `CacheStore` - 180 edges
6. `PipelineResult` - 173 edges
7. `SpiderFootSource` - 164 edges
8. `HarvesterSource` - 162 edges
9. `FinderConfig` - 156 edges
10. `GitHubSource` - 146 edges

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
Cohesion: 0.03
Nodes (114): find(), _finder_config(), FindRequest, _resolve(), VerifyRequest, version(), BaseModel, _check_package() (+106 more)

### Community 1 - "Community 1"
Cohesion: 0.11
Nodes (161): _build_sources(), ColdReach local API server.  Exposes a FastAPI application on localhost:8765 so, Parameters for single-email verification., Parameters for a domain email discovery run., Parameters for single-email verification., Parameters for a domain email discovery run., Build FinderConfig from an API request., Build FinderConfig from an API request.      full_scan=True overrides quick and (+153 more)

### Community 2 - "Community 2"
Cohesion: 0.02
Nodes (95): cache_clear(), cache_list(), Store *result* for *domain* in all available cache layers., Delete cached entries.          Parameters         ----------         domain:, Return all cached domains as (domain, cached_at, is_expired) tuples., Return basic cache statistics., Return a cached DomainResult for *domain*, or ``None`` on miss/expiry., cache_list() (+87 more)

### Community 3 - "Community 3"
Cohesion: 0.03
Nodes (136): ABC, BaseSource, fetch(), Abstract base class for all ColdReach email discovery sources.  Every source fol, Safe wrapper around :meth:`fetch` — never raises.          Returns the results l, A single email address found by a source.      Attributes     ----------     ema, Execution summary for one source run., Abstract base for all email discovery sources.      Subclasses must implement :m (+128 more)

### Community 4 - "Community 4"
Cohesion: 0.04
Nodes (27): ColdReach email discovery sources., learn_format(), Domain email format learner.  Infers a company's email format from confirmed add, Return the most likely email format_name for *domain*.      Analyses the local p, Generate targeted email candidates for *full_name* at *domain*.      When a doma, targeted_patterns(), _clean_name_part(), EmailPattern (+19 more)

### Community 5 - "Community 5"
Cohesion: 0.04
Nodes (43): checkServerOnline(), resolveCompany(), _domain_to_slug(), _is_noreply(), handleUse(), _make_commit(), _mock_json_response(), Unit tests for coldreach.sources.github  All HTTP calls are mocked. (+35 more)

### Community 6 - "Community 6"
Cohesion: 0.06
Nodes (39): check_holehe(), Holehe platform-presence check.  Uses the holehe library (github.com/megadose/ho, Check if *email* is registered on public platforms via holehe.      Parameters, check_reacher(), _parse_reacher_response(), Reacher SMTP verification client.  Reacher (https://reacher.email) is a self-hos, Verify *email* via the Reacher SMTP microservice.      Parameters     ----------, Interpret the Reacher JSON response into a CheckResult. (+31 more)

### Community 7 - "Community 7"
Cohesion: 0.04
Nodes (58): Format Learner: Infers Email Format from Known Emails, generate_patterns(): Email Address Generation, find_emails(config: FinderConfig) Async Entry Point, Python Public API (importable modules), run_basic_pipeline() Async Entry Point, DomainResult: Top-Level Result Pydantic Model, EmailRecord: Per-Email Pydantic Model with Confidence, SourceRecord: Per-Source Discovery Result (+50 more)

### Community 8 - "Community 8"
Cohesion: 0.06
Nodes (18): verify(), BaseSettings, cache_clear(), get_settings(), ColdReach configuration via pydantic-settings.  All settings are read from envir, Return the singleton Settings instance.      Results are cached after the first, All runtime configuration for ColdReach.      Every field can be overridden by a, Settings (+10 more)

### Community 9 - "Community 9"
Cohesion: 0.07
Nodes (14): check_disposable(), is_disposable(), _load_domains(), Disposable / throwaway email domain detection.  Checks whether the domain part o, Parse and cache the bundled disposable domain blocklist.      Returns     ------, Return True if *email* uses a known disposable / throwaway domain.      Paramete, Pipeline checker: fail if email uses a disposable domain.      Parameters     --, Unit tests for coldreach.verify.disposable  All tests are pure CPU — the blockli (+6 more)

### Community 10 - "Community 10"
Cohesion: 0.07
Nodes (29): _drain_job_queue(), find_stream(), _finder_config_v2(), root(), _run_v2_scan(), _sse_event(), _sse_iter(), status() (+21 more)

### Community 11 - "Community 11"
Cohesion: 0.14
Nodes (11): _make_result(), TestExportCSV, TestExportJSON, TestExportValidation, export_results(), Export DomainResult to CSV or JSON.  Format is inferred from the output file ext, Write *result* to *output_path* in CSV or JSON format.      Format is determined, Write one row per email to a UTF-8 CSV file. (+3 more)

### Community 12 - "Community 12"
Cohesion: 0.11
Nodes (29): _find_with_progress(), _banner(), cache(), _configure_logging(), _domain_result_to_dict(), find(), main(), _render_find() (+21 more)

### Community 13 - "Community 13"
Cohesion: 0.1
Nodes (10): check_syntax(), Email syntax validation (RFC 5321 / 5322).  Uses the ``email-validator`` library, Validate an email address against RFC 5322 syntax rules.      Does **not** check, Unit tests for coldreach.verify.syntax.check_syntax  All tests are pure CPU — no, Cases that should PASS syntax validation., Cases that should FAIL syntax validation., Edge cases and unusual but technically valid inputs., TestCheckSyntaxEdgeCases (+2 more)

### Community 14 - "Community 14"
Cohesion: 0.13
Nodes (27): check_dns(), domain_exists(), get_mx_records(), Async DNS / MX record checker.  Resolves MX records for an email's domain to con, Pipeline checker: verify the email's domain has a valid MX record.      Scoring, Resolve MX records for *domain*, sorted by priority (lowest first).      Paramet, Return True if *domain* resolves to at least one A or AAAA record.      Used as, _make_mx_answer() (+19 more)

### Community 15 - "Community 15"
Cohesion: 0.11
Nodes (25): check_catchall(), clear_cache(), is_catch_all(), _probe_via_reacher(), _random_local(), Catch-all domain detection.  A "catch-all" mail server accepts RCPT TO for ANY a, Return True/False/None for catch-all status.      Convenience wrapper around :fu, Send a probe to Reacher. Returns True=catch-all, False=not, None=unknown. (+17 more)

### Community 16 - "Community 16"
Cohesion: 0.17
Nodes (9): _extract_domain_emails(), _build_queries(), _extract_domain_emails(), _query_brave(), _query_ddg_lite(), _query_searxng(), TestExtractDomainEmails, TestBuildQueries (+1 more)

### Community 17 - "Community 17"
Cohesion: 0.08
Nodes (11): detectGreenhouse(), detectIndeed(), detect(), run(), detectLever(), detectLinkedIn(), ColdReach core Pydantic models.  These are the primary data structures that flow, Return current UTC time as a timezone-naive datetime. (+3 more)

### Community 18 - "Community 18"
Cohesion: 0.24
Nodes (3): _classify_path(), _is_junk(), TestClassifyPath

### Community 19 - "Community 19"
Cohesion: 0.36
Nodes (11): append_decisions(), append_handoff(), append_progress(), ensure_context_files(), git_branch(), main(), now_stamp(), parse_args() (+3 more)

### Community 20 - "Community 20"
Cohesion: 0.29
Nodes (3): Accepts both 'EMAILADDR' and 'Email Address' type strings., Emails like 'user@acme.com [apollo.io]' should be cleaned., TestSpiderFootSourceParseOutput

### Community 21 - "Community 21"
Cohesion: 0.39
Nodes (1): TestHarvesterSourceFilterEmails

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (2): Role Emails: Always-On info/sales/contact Candidates, Pattern Generator Source: Name + Format Inference

### Community 35 - "Community 35"
Cohesion: 1.0
Nodes (1): True if a Groq API key is configured.

### Community 36 - "Community 36"
Cohesion: 1.0
Nodes (1): True if the database backend is SQLite (no Docker needed).

### Community 37 - "Community 37"
Cohesion: 1.0
Nodes (1): True if status is PASS.

### Community 38 - "Community 38"
Cohesion: 1.0
Nodes (1): True if status is FAIL.

### Community 39 - "Community 39"
Cohesion: 1.0
Nodes (1): True if status is WARN.

### Community 40 - "Community 40"
Cohesion: 1.0
Nodes (1): True if status is SKIP.

### Community 41 - "Community 41"
Cohesion: 1.0
Nodes (1): Create a passing result.

### Community 42 - "Community 42"
Cohesion: 1.0
Nodes (1): Create a failing result.

### Community 43 - "Community 43"
Cohesion: 1.0
Nodes (1): Create a warning result.

### Community 44 - "Community 44"
Cohesion: 1.0
Nodes (1): Create a skipped result.

### Community 45 - "Community 45"
Cohesion: 1.0
Nodes (1): Lowercase and strip whitespace.

### Community 46 - "Community 46"
Cohesion: 1.0
Nodes (1): The domain part of the email address.

### Community 47 - "Community 47"
Cohesion: 1.0
Nodes (1): The local (username) part of the email address.

### Community 48 - "Community 48"
Cohesion: 1.0
Nodes (1): Deduplicated list of source identifiers that found this email.

### Community 49 - "Community 49"
Cohesion: 1.0
Nodes (1): The highest-priority source that found this email.

### Community 50 - "Community 50"
Cohesion: 1.0
Nodes (1): Return the email with the highest confidence score.

### Community 53 - "Community 53"
Cohesion: 1.0
Nodes (1): Install status of an optional Python package.

### Community 54 - "Community 54"
Cohesion: 1.0
Nodes (1): Aggregated result from a full diagnostics run.

### Community 55 - "Community 55"
Cohesion: 1.0
Nodes (1): HTTP GET with timing; never raises.

### Community 56 - "Community 56"
Cohesion: 1.0
Nodes (1): Run all checks concurrently and return a DiagnosticsReport.      Parameters

### Community 57 - "Community 57"
Cohesion: 1.0
Nodes (1): Ping all services and return {name: online}.  Fast path for find command.

### Community 58 - "Community 58"
Cohesion: 1.0
Nodes (1): WhoisSource: Domain Registrant Contact Email

### Community 59 - "Community 59"
Cohesion: 1.0
Nodes (1): RedditSource: Post Body/Comment Email Extraction

### Community 60 - "Community 60"
Cohesion: 1.0
Nodes (1): SearchEngineSource: SearXNG → DDG → Brave Fallback Chain

### Community 61 - "Community 61"
Cohesion: 1.0
Nodes (1): CLI: coldreach cache list/stats/clear

### Community 62 - "Community 62"
Cohesion: 1.0
Nodes (1): CLI Exit Codes: 0=pass, 1=fail, 2=usage error

### Community 63 - "Community 63"
Cohesion: 1.0
Nodes (1): Dev Install: uv sync --all-extras --dev

### Community 64 - "Community 64"
Cohesion: 1.0
Nodes (1): Project PLAN.md: Feature Roadmap and Architecture Notes

## Knowledge Gaps
- **114 isolated node(s):** `ColdReach configuration via pydantic-settings.  All settings are read from envir`, `All runtime configuration for ColdReach.      Every field can be overridden by a`, `True if a Groq API key is configured.`, `True if the database backend is SQLite (no Docker needed).`, `Return the singleton Settings instance.      Results are cached after the first` (+109 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 21`** (9 nodes): `._filter_emails()`, `TestHarvesterSourceFilterEmails`, `.test_accepts_subdomain_emails()`, `.test_deduplicates()`, `.test_empty_input()`, `.test_keeps_domain_emails()`, `.test_normalises_to_lowercase()`, `.test_rejects_html_encoded_emails()`, `.test_removes_other_domains()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (2 nodes): `Role Emails: Always-On info/sales/contact Candidates`, `Pattern Generator Source: Name + Format Inference`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (1 nodes): `True if a Groq API key is configured.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 36`** (1 nodes): `True if the database backend is SQLite (no Docker needed).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 37`** (1 nodes): `True if status is PASS.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 38`** (1 nodes): `True if status is FAIL.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 39`** (1 nodes): `True if status is WARN.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 40`** (1 nodes): `True if status is SKIP.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (1 nodes): `Create a passing result.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (1 nodes): `Create a failing result.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 43`** (1 nodes): `Create a warning result.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 44`** (1 nodes): `Create a skipped result.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 45`** (1 nodes): `Lowercase and strip whitespace.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 46`** (1 nodes): `The domain part of the email address.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 47`** (1 nodes): `The local (username) part of the email address.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 48`** (1 nodes): `Deduplicated list of source identifiers that found this email.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 49`** (1 nodes): `The highest-priority source that found this email.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 50`** (1 nodes): `Return the email with the highest confidence score.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 53`** (1 nodes): `Install status of an optional Python package.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 54`** (1 nodes): `Aggregated result from a full diagnostics run.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 55`** (1 nodes): `HTTP GET with timing; never raises.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 56`** (1 nodes): `Run all checks concurrently and return a DiagnosticsReport.      Parameters`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 57`** (1 nodes): `Ping all services and return {name: online}.  Fast path for find command.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 58`** (1 nodes): `WhoisSource: Domain Registrant Contact Email`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 59`** (1 nodes): `RedditSource: Post Body/Comment Email Extraction`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 60`** (1 nodes): `SearchEngineSource: SearXNG → DDG → Brave Fallback Chain`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 61`** (1 nodes): `CLI: coldreach cache list/stats/clear`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 62`** (1 nodes): `CLI Exit Codes: 0=pass, 1=fail, 2=usage error`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 63`** (1 nodes): `Dev Install: uv sync --all-extras --dev`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 64`** (1 nodes): `Project PLAN.md: Feature Roadmap and Architecture Notes`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `EmailSource` connect `Community 3` to `Community 0`, `Community 1`, `Community 2`, `Community 5`, `Community 11`, `Community 16`, `Community 17`, `Community 18`, `Community 20`, `Community 21`?**
  _High betweenness centrality (0.121) - this node is a cross-community bridge._
- **Why does `find_emails()` connect `Community 12` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 10`?**
  _High betweenness centrality (0.096) - this node is a cross-community bridge._
- **Why does `run_basic_pipeline()` connect `Community 12` to `Community 0`, `Community 1`, `Community 2`, `Community 6`, `Community 8`, `Community 9`, `Community 13`, `Community 14`?**
  _High betweenness centrality (0.086) - this node is a cross-community bridge._
- **Are the 261 inferred relationships involving `SourceResult` (e.g. with `ScanJob` and `FindRequest`) actually correct?**
  _`SourceResult` has 261 INFERRED edges - model-reasoned connections that need verification._
- **Are the 247 inferred relationships involving `BaseSource` (e.g. with `ScanJob` and `FindRequest`) actually correct?**
  _`BaseSource` has 247 INFERRED edges - model-reasoned connections that need verification._
- **Are the 206 inferred relationships involving `DomainResult` (e.g. with `ScanJob` and `FindRequest`) actually correct?**
  _`DomainResult` has 206 INFERRED edges - model-reasoned connections that need verification._
- **Are the 197 inferred relationships involving `EmailSource` (e.g. with `FinderConfig` and `find_emails() — the main orchestrator.  Runs all configured sources concurrently`) actually correct?**
  _`EmailSource` has 197 INFERRED edges - model-reasoned connections that need verification._