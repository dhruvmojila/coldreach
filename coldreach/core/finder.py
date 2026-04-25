"""
find_emails() — the main orchestrator.

Runs all configured sources concurrently, deduplicates results,
runs the verification pipeline on each candidate, and returns a
ranked DomainResult.

Design
------
- Sources run in parallel via asyncio.gather (fire-and-forget per source)
- Each source's results are merged into a shared email→SourceRecord map
- After all sources complete, the verification pipeline scores each email
- Final DomainResult is sorted by confidence descending

Source precedence for confidence_hint (added on top of pipeline score):
  website/contact  +35
  website/team     +30
  website/about    +25
  github/commit    +25
  whois            +20
  reddit           +15
  website/generic  +15
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from coldreach.core.models import (
    DomainResult,
    EmailRecord,
    EmailSource,
    SourceRecord,
    VerificationStatus,
)
from coldreach.generate.learner import targeted_patterns
from coldreach.generate.patterns import generate_role_emails
from coldreach.sources.base import BaseSource, SourceResult
from coldreach.sources.crawl4ai_source import Crawl4AISource
from coldreach.sources.firecrawl import FirecrawlSource
from coldreach.sources.github import GitHubSource
from coldreach.sources.harvester import HarvesterSource
from coldreach.sources.reddit import RedditSource
from coldreach.sources.search_engine import SearchEngineSource
from coldreach.sources.spiderfoot import SpiderFootSource
from coldreach.sources.web_crawler import WebCrawlerSource
from coldreach.sources.whois_source import WhoisSource
from coldreach.storage.cache import CacheStore
from coldreach.verify.pipeline import run_basic_pipeline

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class FinderConfig:
    """Runtime options for find_emails().

    Attributes
    ----------
    use_web_crawler:
        Crawl company website pages.
    use_whois:
        Query WHOIS for registrant contact emails.
    use_github:
        Mine public GitHub commits for domain emails.
    use_reddit:
        Search Reddit for domain email mentions.
    github_token:
        Optional GitHub PAT for higher rate limits (5000/hr vs 60/hr).
    min_confidence:
        Exclude emails below this confidence from the final result.
    request_timeout:
        Per-source HTTP timeout in seconds.
    max_concurrent_sources:
        Maximum number of sources to run simultaneously.
    """

    use_web_crawler: bool = True
    use_whois: bool = True
    use_github: bool = True
    use_reddit: bool = True
    use_search_engine: bool = True
    use_harvester: bool = True
    use_spiderfoot: bool = True
    use_firecrawl: bool = False  # opt-in: requires firecrawl-py + Docker stack
    use_crawl4ai: bool = False  # opt-in: requires pip install crawl4ai + playwright
    use_role_emails: bool = True  # generate info@/sales@/contact@ candidates
    github_token: str | None = None
    searxng_url: str | None = "http://localhost:8088"
    firecrawl_url: str = "http://localhost:3002"
    brave_api_key: str | None = None
    spiderfoot_container: str = "coldreach-spiderfoot"
    spiderfoot_max_wait: float = 600.0  # SpiderFoot passive scan can take 5-10 min
    harvester_container: str = "coldreach-theharvester"
    harvester_max_wait: float = 300.0  # theHarvester across free sources ~2-4 min
    harvester_sources: str | None = None  # None = free sources; "all" = all sources
    reacher_url: str | None = "http://localhost:8083"
    use_reacher: bool = True
    use_holehe: bool = False  # opt-in — slow (~30s per email)
    cache_db: str | None = "~/.coldreach/cache.db"
    redis_url: str | None = None
    cache_ttl_days: int = 7
    use_cache: bool = True
    refresh_cache: bool = False  # if True, ignore cached result but still overwrite
    min_confidence: int = 0
    request_timeout: float = 10.0
    max_concurrent_sources: int = 6


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _merge_results(
    raw: list[SourceResult],
) -> dict[str, list[SourceResult]]:
    """Group SourceResults by normalised email address."""
    grouped: dict[str, list[SourceResult]] = {}
    for r in raw:
        key = r.email.strip().lower()
        if "@" not in key:
            continue
        grouped.setdefault(key, []).append(r)
    return grouped


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


async def find_emails(
    domain: str,
    *,
    person_name: str | None = None,
    config: FinderConfig | None = None,
) -> DomainResult:
    """Discover and verify all email addresses for *domain*.

    Parameters
    ----------
    domain:
        Target domain, e.g. ``"stripe.com"``.
    person_name:
        Optional full name for pattern-based narrowing.
    config:
        Finder configuration. Uses sensible defaults if not provided.

    Returns
    -------
    DomainResult
        All discovered, verified, and ranked email addresses for *domain*.
    """
    cfg = config or FinderConfig()
    domain = domain.strip().lower().removeprefix("www.")

    # ── Cache lookup ──────────────────────────────────────────────────────────
    cache: CacheStore | None = None
    if cfg.use_cache and cfg.cache_db:
        cache = CacheStore(
            db_path=cfg.cache_db,
            redis_url=cfg.redis_url,
            ttl_days=cfg.cache_ttl_days,
        )
        if not cfg.refresh_cache:
            cached = cache.get(domain)
            if cached is not None:
                logger.info("Cache hit for %s — skipping sources", domain)
                cached.emails = cached.sorted_emails(min_confidence=cfg.min_confidence)
                return cached

    # ── Build source list ─────────────────────────────────────────────────────
    sources: list[BaseSource] = []
    if cfg.use_web_crawler:
        sources.append(WebCrawlerSource(timeout=cfg.request_timeout))
    if cfg.use_whois:
        sources.append(WhoisSource(timeout=cfg.request_timeout))
    if cfg.use_github:
        sources.append(GitHubSource(token=cfg.github_token, timeout=cfg.request_timeout))
    if cfg.use_reddit:
        sources.append(RedditSource(timeout=cfg.request_timeout))
    if cfg.use_search_engine:
        sources.append(
            SearchEngineSource(
                searxng_url=cfg.searxng_url,
                brave_api_key=cfg.brave_api_key,
                timeout=cfg.request_timeout,
            )
        )
    if cfg.use_harvester:
        sources.append(
            HarvesterSource(
                container=cfg.harvester_container,
                sources=cfg.harvester_sources,
                max_wait=cfg.harvester_max_wait,
            )
        )
    if cfg.use_spiderfoot:
        sources.append(
            SpiderFootSource(
                container=cfg.spiderfoot_container,
                max_wait=cfg.spiderfoot_max_wait,
            )
        )
    if cfg.use_firecrawl:
        sources.append(
            FirecrawlSource(firecrawl_url=cfg.firecrawl_url, timeout=cfg.request_timeout)
        )
    if cfg.use_crawl4ai:
        sources.append(Crawl4AISource(timeout=cfg.request_timeout))

    logger.info("Running %d source(s) for domain: %s", len(sources), domain)

    # ── Run sources concurrently (semaphore-limited) ──────────────────────────
    sem = asyncio.Semaphore(cfg.max_concurrent_sources)

    async def _run_source(src: BaseSource) -> list[SourceResult]:
        async with sem:
            results, summary = await src.run(domain, person_name=person_name)
            if summary.errors:
                logger.warning("[%s] errors: %s", src.name, "; ".join(summary.errors))
            return results

    all_results_nested = await asyncio.gather(*[_run_source(s) for s in sources])
    all_raw: list[SourceResult] = [r for batch in all_results_nested for r in batch]

    logger.info("Sources returned %d raw email candidate(s) for %s", len(all_raw), domain)

    # ── Pattern generation (when person_name is given) ────────────────────────
    if person_name:
        found_emails = [r.email for r in all_raw]
        # Higher confidence_hint when format is inferred from real emails
        has_known = bool(found_emails)
        patterns = targeted_patterns(person_name, domain, found_emails)
        for pat in patterns:
            all_raw.append(
                SourceResult(
                    email=pat.email,
                    source=EmailSource.PATTERN_GENERATED,
                    url="",
                    context=f"pattern: {pat.format_name}",
                    confidence_hint=10 if has_known else 5,
                )
            )
        if patterns:
            logger.debug(
                "Pattern learner added %d candidate(s) for '%s' at %s",
                len(patterns),
                person_name,
                domain,
            )

    # ── Role emails (info@, sales@, contact@, …) ──────────────────────────────
    if cfg.use_role_emails:
        existing = {r.email.strip().lower() for r in all_raw}
        for rp in generate_role_emails(domain):
            if rp.email not in existing:
                all_raw.append(
                    SourceResult(
                        email=rp.email,
                        source=EmailSource.PATTERN_GENERATED,
                        url="",
                        context=rp.format_name,
                        confidence_hint=5,
                    )
                )

    # ── Deduplicate + build source map ────────────────────────────────────────
    grouped = _merge_results(all_raw)

    # ── Verify each unique candidate ──────────────────────────────────────────
    domain_result = DomainResult(domain=domain)

    reacher_url = cfg.reacher_url if cfg.use_reacher else None

    for email, source_results in grouped.items():
        pipeline = await run_basic_pipeline(
            email,
            reacher_url=reacher_url,
            run_holehe=cfg.use_holehe,
        )

        # Cumulative confidence: pipeline score + sum of source hints (clamped)
        source_hint = sum(sr.confidence_hint for sr in source_results)
        confidence = min(100, pipeline.score + source_hint)

        # Map pipeline result to VerificationStatus
        reacher_check = pipeline.checks.get("reacher")
        if not pipeline.passed:
            status = VerificationStatus.INVALID
            confidence = 0
        elif reacher_check and reacher_check.passed:
            status = VerificationStatus.VALID
        elif reacher_check and reacher_check.warned:
            status = VerificationStatus.CATCH_ALL
        elif reacher_check and reacher_check.failed:
            status = VerificationStatus.UNDELIVERABLE
        elif pipeline.mx_records:
            status = VerificationStatus.UNKNOWN  # DNS OK, SMTP not verified
        else:
            status = VerificationStatus.RISKY

        # Build SourceRecord list (deduplicated by source type)
        seen_sources: set[EmailSource] = set()
        source_records: list[SourceRecord] = []
        for sr in source_results:
            if sr.source not in seen_sources:
                seen_sources.add(sr.source)
                source_records.append(
                    SourceRecord(
                        source=sr.source,
                        url=sr.url or None,
                        context=sr.context,
                    )
                )

        record = EmailRecord(
            email=pipeline.normalized_email,
            confidence=confidence,
            status=status,
            sources=source_records,
            mx_records=pipeline.mx_records,
        )
        domain_result.add_email(record)

    # ── Store full result in cache (before min_confidence filter) ────────────
    if cache is not None:
        cache.set(domain, domain_result)

    # ── Filter + sort ─────────────────────────────────────────────────────────
    domain_result.emails = domain_result.sorted_emails(min_confidence=cfg.min_confidence)

    logger.info(
        "find_emails complete for %s: %d verified email(s)", domain, len(domain_result.emails)
    )
    return domain_result
