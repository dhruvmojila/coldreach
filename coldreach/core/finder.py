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
from coldreach.sources.base import BaseSource, SourceResult
from coldreach.sources.github import GitHubSource
from coldreach.sources.harvester import HarvesterSource
from coldreach.sources.reddit import RedditSource
from coldreach.sources.search_engine import SearchEngineSource
from coldreach.sources.web_crawler import WebCrawlerSource
from coldreach.sources.whois_source import WhoisSource
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
    github_token: str | None = None
    searxng_url: str | None = "http://localhost:8080"
    brave_api_key: str | None = None
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
        sources.append(HarvesterSource(timeout=60.0))

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

    # ── Deduplicate + build source map ────────────────────────────────────────
    grouped = _merge_results(all_raw)

    # ── Verify each unique candidate ──────────────────────────────────────────
    domain_result = DomainResult(domain=domain)

    for email, source_results in grouped.items():
        pipeline = await run_basic_pipeline(email)

        # Aggregate confidence hints from all sources that found this email
        max_hint = max((sr.confidence_hint for sr in source_results), default=0)

        # Pipeline base score + source hint, clamped [0,100]
        confidence = min(100, pipeline.score + max_hint)

        # Map pipeline result to VerificationStatus
        if not pipeline.passed:
            status = VerificationStatus.INVALID
            confidence = 0
        elif pipeline.mx_records:
            status = VerificationStatus.UNKNOWN  # DNS OK, SMTP not yet checked
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

    # ── Filter + sort ─────────────────────────────────────────────────────────
    domain_result.emails = domain_result.sorted_emails(min_confidence=cfg.min_confidence)

    logger.info(
        "find_emails complete for %s: %d verified email(s)", domain, len(domain_result.emails)
    )
    return domain_result
