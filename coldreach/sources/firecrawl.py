"""
Firecrawl source — JS-heavy website scraping via self-hosted Firecrawl.

Scrapes contact/about/team pages using the Firecrawl SDK, which handles
JS-rendered content that plain httpx crawling misses.  Also discovers
relevant pages via sitemap.xml before scraping.

Requires:
  - firecrawl-py installed (pip install firecrawl-py)
  - Self-hosted Firecrawl server (see https://github.com/mendableai/firecrawl)

Skips gracefully if the SDK is not installed or the server is unreachable.

SDK compatibility: handles both firecrawl-py >= 1.0 (Firecrawl class) and
older versions (FirecrawlApp class) transparently.
"""

from __future__ import annotations

import asyncio
import logging
import re
import urllib.parse
from xml.etree import ElementTree

import httpx

from coldreach.core.models import EmailSource
from coldreach.sources.base import BaseSource, SourceResult

logger = logging.getLogger(__name__)

# ── SDK import — handle both old (FirecrawlApp) and new (Firecrawl) ──────────
_APP_CLASS: type | None = None
_SCRAPE_METHOD: str | None = None

try:
    from firecrawl import Firecrawl as _NewClient  # type: ignore[import]

    _APP_CLASS = _NewClient
    _SCRAPE_METHOD = "v2"
    logger.debug("firecrawl: using new SDK (Firecrawl class)")
except ImportError:
    try:
        from firecrawl import FirecrawlApp as _OldClient  # type: ignore[import]

        _APP_CLASS = _OldClient
        _SCRAPE_METHOD = "v1"
        logger.debug("firecrawl: using old SDK (FirecrawlApp class)")
    except ImportError:
        logger.debug("firecrawl-py not installed — run: pip install firecrawl-py")

# ── Constants ─────────────────────────────────────────────────────────────────

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

_SKIP_EMAIL_DOMAINS = frozenset(
    {"example.com", "sentry.io", "yourdomain.com", "email.com", "domain.com", "company.com"}
)

_CONTACT_KEYWORDS = frozenset(
    {"contact", "about", "team", "people", "staff", "company", "who-we-are", "meet", "leadership"}
)

_HARDCODED_PATHS = [
    "/contact",
    "/contact-us",
    "/about",
    "/about-us",
    "/team",
    "/our-team",
    "/people",
    "/staff",
    "/leadership",
]

_PATH_SOURCE_MAP: dict[str, EmailSource] = {
    "/contact": EmailSource.WEBSITE_CONTACT,
    "/contact-us": EmailSource.WEBSITE_CONTACT,
    "/about": EmailSource.WEBSITE_ABOUT,
    "/about-us": EmailSource.WEBSITE_ABOUT,
    "/team": EmailSource.WEBSITE_TEAM,
    "/our-team": EmailSource.WEBSITE_TEAM,
    "/people": EmailSource.WEBSITE_TEAM,
    "/staff": EmailSource.WEBSITE_TEAM,
    "/leadership": EmailSource.WEBSITE_TEAM,
}

_CONFIDENCE_HINT: dict[EmailSource, int] = {
    EmailSource.WEBSITE_CONTACT: 35,
    EmailSource.WEBSITE_TEAM: 30,
    EmailSource.WEBSITE_ABOUT: 25,
    EmailSource.WEBSITE_GENERIC: 15,
}

_HEADERS = {"User-Agent": "ColdReach/0.1 (firecrawl source)"}


# ── Helpers ───────────────────────────────────────────────────────────────────


def _classify_path(path: str) -> EmailSource:
    for prefix, source in _PATH_SOURCE_MAP.items():
        if path.lower().startswith(prefix):
            return source
    return EmailSource.WEBSITE_GENERIC


def _extract_emails_for_domain(text: str, domain: str) -> list[str]:
    """Extract emails from scraped text, keeping only those at *domain*."""
    found: list[str] = []
    seen: set[str] = set()
    for match in _EMAIL_RE.finditer(text):
        addr = match.group(0).lower()
        if addr in seen:
            continue
        if "@" not in addr:
            continue
        email_domain = addr.split("@")[1]
        if email_domain in _SKIP_EMAIL_DOMAINS:
            continue
        if email_domain == domain or email_domain.endswith(f".{domain}"):
            seen.add(addr)
            found.append(addr)
    return found


def _scrape_with_sdk(app: object, url: str) -> str:
    """Call the Firecrawl SDK synchronously (run via asyncio.to_thread)."""
    try:
        if _SCRAPE_METHOD == "v2":
            result = app.scrape(url, formats=["markdown"])  # type: ignore[union-attr]
            if hasattr(result, "markdown"):
                return (result.markdown or "")[:4000]
            if isinstance(result, dict):
                return (result.get("markdown") or result.get("content") or "")[:4000]
        else:
            result = app.scrape_url(url, formats=["markdown"])  # type: ignore[union-attr]
            if isinstance(result, dict):
                return (result.get("markdown") or result.get("content") or "")[:4000]
            if hasattr(result, "markdown"):
                return (result.markdown or "")[:4000]
    except Exception as exc:
        logger.debug("Firecrawl scrape failed for %s: %s", url, exc)
    return ""


# ── Source ────────────────────────────────────────────────────────────────────


class FirecrawlSource(BaseSource):
    """Scrape company pages via self-hosted Firecrawl for JS-rendered content.

    Discovers pages via sitemap.xml first, then falls back to hardcoded
    contact/about/team paths.  Extracts emails from markdown output.

    Parameters
    ----------
    firecrawl_url:
        Base URL of the self-hosted Firecrawl server (e.g. ``"http://localhost:3002"``).
    timeout:
        HTTP timeout for availability + sitemap requests.
    """

    name = "firecrawl"

    def __init__(
        self,
        firecrawl_url: str = "http://localhost:3002",
        timeout: float = 30.0,
    ) -> None:
        super().__init__(timeout=timeout)
        self.firecrawl_url = firecrawl_url.rstrip("/")

    async def fetch(
        self,
        domain: str,
        *,
        person_name: str | None = None,
    ) -> list[SourceResult]:
        if _APP_CLASS is None:
            self._log.debug("firecrawl-py not installed — skipping")
            return []

        if not await self._is_available():
            self._log.debug("Firecrawl server not reachable at %s", self.firecrawl_url)
            return []

        app = _APP_CLASS(api_key="self-hosted", api_url=self.firecrawl_url)
        pages = await self._get_pages_to_scrape(domain)
        self._log.debug("Firecrawl: will try %d pages for %s", len(pages), domain)

        results: list[SourceResult] = []
        seen_emails: set[str] = set()
        combined_len = 0

        for url in pages:
            if combined_len > 8000:
                break
            content = await asyncio.to_thread(_scrape_with_sdk, app, url)
            if not content or len(content) < 150:
                continue
            combined_len += len(content)
            path = urllib.parse.urlparse(url).path or "/"
            source_type = _classify_path(path)
            for email in _extract_emails_for_domain(content, domain):
                if email not in seen_emails:
                    seen_emails.add(email)
                    results.append(
                        SourceResult(
                            email=email,
                            source=source_type,
                            url=url,
                            context="firecrawl",
                            confidence_hint=_CONFIDENCE_HINT.get(source_type, 15),
                        )
                    )

        self._log.debug(
            "Firecrawl found %d email(s) from %d pages for %s",
            len(results),
            len(pages),
            domain,
        )
        return results

    async def _is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{self.firecrawl_url}/", headers=_HEADERS, follow_redirects=True
                )
                return resp.status_code in (200, 404)
        except Exception:
            return False

    async def _get_pages_to_scrape(self, domain: str) -> list[str]:
        sitemap_pages = await self._fetch_sitemap_pages(domain)
        hardcoded = [f"https://{domain}{p}" for p in _HARDCODED_PATHS] + [f"https://{domain}"]
        seen: set[str] = set()
        pages: list[str] = []
        for url in sitemap_pages + hardcoded:
            if url not in seen:
                seen.add(url)
                pages.append(url)
        return pages[:12]

    async def _fetch_sitemap_pages(self, domain: str) -> list[str]:
        """Fetch sitemap.xml and extract contact/about/team URLs."""
        sitemap_urls = [
            f"https://{domain}/sitemap.xml",
            f"https://www.{domain}/sitemap.xml",
        ]
        candidates: list[str] = []
        async with httpx.AsyncClient(timeout=self.timeout, headers=_HEADERS) as client:
            for sitemap_url in sitemap_urls:
                try:
                    resp = await client.get(sitemap_url, follow_redirects=True)
                    if resp.status_code != 200:
                        continue
                    root = ElementTree.fromstring(resp.text)
                    all_locs = [
                        el.text.strip()
                        for el in root.iter(
                            "{http://www.sitemaps.org/schemas/sitemap/0.9}loc"
                        )
                        if el.text
                    ]
                    for loc in all_locs:
                        path = urllib.parse.urlparse(loc).path.lower().strip("/")
                        parts = set(re.split(r"[-/]", path))
                        if parts & _CONTACT_KEYWORDS:
                            candidates.append(loc)
                    if candidates:
                        break
                except Exception as exc:
                    self._log.debug("Sitemap parse failed for %s: %s", domain, exc)

        seen: set[str] = set()
        result: list[str] = []
        for url in candidates:
            if url not in seen:
                seen.add(url)
                result.append(url)
            if len(result) >= 10:
                break
        return result
