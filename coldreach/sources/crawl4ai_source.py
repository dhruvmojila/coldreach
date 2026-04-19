"""
Crawl4AI source — Playwright-based JS rendering for SPA company websites.

Handles JS-heavy sites that plain httpx crawling (`web_crawler.py`) misses.
The two sources are complementary: `web_crawler` runs for all sites, while
`crawl4ai` adds a JS rendering pass for sites where httpx returns no emails.

Requires:
  - crawl4ai installed: pip install crawl4ai
  - Playwright browsers: crawl4ai-setup  (runs playwright install)

Skips gracefully if crawl4ai is not installed.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any
from urllib.parse import urlparse

from coldreach.core.models import EmailSource
from coldreach.sources.base import BaseSource, SourceResult

logger = logging.getLogger(__name__)

try:
    from crawl4ai import AsyncWebCrawler, CacheMode

    _CRAWL4AI_AVAILABLE = True
except ImportError:
    _CRAWL4AI_AVAILABLE = False
    logger.debug("crawl4ai not installed — run: pip install crawl4ai && crawl4ai-setup")

# ── Constants ─────────────────────────────────────────────────────────────────

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

# Phrases indicating a bot-block or JS-required error page — discard content
_JUNK_PHRASES = [
    "javascript is disabled",
    "enable javascript",
    "verify you're not a robot",
    "please enable cookies",
    "access denied",
    "checking your browser",
    "ddos protection",
    "ray id",
    "cf-browser-verification",
]

# Known anti-bot platforms — never useful as leads, skip them
_SKIP_DOMAINS = frozenset(
    {
        "booking.com",
        "expedia.com",
        "google.com",
        "linkedin.com",
        "facebook.com",
        "twitter.com",
        "instagram.com",
        "airbnb.com",
    }
)

_PAGES_TO_TRY = [
    "",
    "/contact",
    "/contact-us",
    "/about",
    "/about-us",
    "/team",
    "/our-team",
    "/people",
]

_PATH_SOURCE_MAP: dict[str, EmailSource] = {
    "/contact": EmailSource.WEBSITE_CONTACT,
    "/contact-us": EmailSource.WEBSITE_CONTACT,
    "/about": EmailSource.WEBSITE_ABOUT,
    "/about-us": EmailSource.WEBSITE_ABOUT,
    "/team": EmailSource.WEBSITE_TEAM,
    "/our-team": EmailSource.WEBSITE_TEAM,
    "/people": EmailSource.WEBSITE_TEAM,
}

_CONFIDENCE_HINT: dict[EmailSource, int] = {
    EmailSource.WEBSITE_CONTACT: 35,
    EmailSource.WEBSITE_TEAM: 30,
    EmailSource.WEBSITE_ABOUT: 25,
    EmailSource.WEBSITE_GENERIC: 15,
}


# ── Helpers ───────────────────────────────────────────────────────────────────


def _classify_path(path: str) -> EmailSource:
    for prefix, source in _PATH_SOURCE_MAP.items():
        if path.lower().startswith(prefix):
            return source
    return EmailSource.WEBSITE_GENERIC


def _is_junk(text: str) -> bool:
    """Return True if content looks like a bot-block or empty page."""
    if len(text) < 300:
        return True
    lowered = text.lower()
    return any(phrase in lowered for phrase in _JUNK_PHRASES)


# ── Source ────────────────────────────────────────────────────────────────────


class Crawl4AISource(BaseSource):
    """Crawl company pages with Playwright JS rendering via crawl4ai.

    Handles JS-heavy SPAs that return blank pages with plain httpx.
    Runs alongside ``WebCrawlerSource`` — only adds emails not already found.

    Parameters
    ----------
    page_timeout:
        Playwright page load timeout in milliseconds.
    timeout:
        asyncio.wait_for timeout in seconds wrapping each page crawl.
    """

    name = "crawl4ai"

    def __init__(self, timeout: float = 30.0, page_timeout: int = 15000) -> None:
        super().__init__(timeout=timeout)
        self.page_timeout = page_timeout

    async def fetch(
        self,
        domain: str,
        *,
        person_name: str | None = None,
    ) -> list[SourceResult]:
        if not _CRAWL4AI_AVAILABLE:
            self._log.debug("crawl4ai not installed — skipping")
            return []

        clean = domain.lower().replace("www.", "")
        if clean in _SKIP_DOMAINS:
            self._log.debug("Skipping known anti-bot domain: %s", domain)
            return []

        results: list[SourceResult] = []
        seen_emails: set[str] = set()

        async with AsyncWebCrawler(headless=True, verbose=False) as crawler:
            for path in _PAGES_TO_TRY:
                url = f"https://{domain}{path}"
                content = await self._fetch_page(crawler, url)
                if not content:
                    continue

                path_part = urlparse(url).path or "/"
                source_type = _classify_path(path_part)

                for match in _EMAIL_RE.finditer(content):
                    addr = match.group(0).lower()
                    if addr in seen_emails:
                        continue
                    email_domain = addr.split("@")[1] if "@" in addr else ""
                    if email_domain != domain and not email_domain.endswith(f".{domain}"):
                        continue
                    seen_emails.add(addr)
                    results.append(
                        SourceResult(
                            email=addr,
                            source=source_type,
                            url=url,
                            context="crawl4ai",
                            confidence_hint=_CONFIDENCE_HINT.get(source_type, 15),
                        )
                    )

        self._log.debug("Crawl4AI found %d email(s) for %s", len(results), domain)
        return results

    async def _fetch_page(self, crawler: Any, url: str) -> str | None:
        try:
            result = await asyncio.wait_for(
                crawler.arun(
                    url=url,
                    cache_mode=CacheMode.ENABLED,
                    word_count_threshold=10,
                    exclude_external_links=True,
                    process_iframes=False,
                    remove_overlay_elements=True,
                    page_timeout=self.page_timeout,
                    wait_until="domcontentloaded",
                ),
                timeout=self.timeout,
            )
            if result.success and result.markdown and not _is_junk(result.markdown):
                return str(result.markdown[:3000])
            self._log.debug(
                "crawl4ai: %s — %s",
                url,
                getattr(result, "error_message", "no content"),
            )
        except TimeoutError:
            self._log.debug("crawl4ai: timeout on %s", url)
        except Exception as exc:
            self._log.debug("crawl4ai error for %s: %s", url, exc)
        return None
