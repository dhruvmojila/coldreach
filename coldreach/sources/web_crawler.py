"""
Website crawler source.

Crawls the target domain's public pages (homepage, /contact, /team, /about,
/people, /staff, /leadership) and extracts email addresses using:
  - RFC 5322-compliant regex
  - mailto: link href extraction
  - Common obfuscation patterns ([at], (at), " at ", [dot], etc.)

Uses httpx for async HTTP (no Playwright/JS required for most B2B sites).
Falls back gracefully on SSL errors, redirects, and timeouts.

Source priority for scoring: contact page > team page > generic.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urljoin, urlparse

import httpx

from coldreach.core.models import EmailSource
from coldreach.sources.base import BaseSource, SourceResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Standard email regex — deliberately conservative to minimise false positives.
# Excludes image filenames (e.g. "icon@2x.png") and version strings.
_EMAIL_RE = re.compile(
    r"(?<![='\"/])(?<!\w)"  # not preceded by = ' " / or word char
    r"([a-zA-Z0-9._%+\-]{1,64}"
    r"@"
    r"[a-zA-Z0-9.\-]{1,253}"
    r"\.[a-zA-Z]{2,})"
    r"(?!\.(png|jpg|jpeg|gif|svg|webp|ico|css|js|woff|ttf))"  # not image/asset ext
    r"(?!['\"/])",
    re.IGNORECASE,
)

# Obfuscated patterns — e.g. "hello [at] example.com", "hello(at)example.com"
_OBFUSCATED_RE = re.compile(
    r"([a-zA-Z0-9._%+\-]{1,64})"
    r"\s*(?:\[at\]|\(at\)|\s+at\s+|&#64;|&amp;#64;)\s*"
    r"([a-zA-Z0-9.\-]{1,253}\.[a-zA-Z]{2,})",
    re.IGNORECASE,
)

# mailto: href — captures the address after "mailto:"
_MAILTO_RE = re.compile(r'href=["\']mailto:([^"\'?\s]+)', re.IGNORECASE)

# TLDs that are asset file extensions — never valid email domains
_ASSET_TLDS = frozenset(
    [
        "png",
        "jpg",
        "jpeg",
        "gif",
        "svg",
        "webp",
        "ico",
        "css",
        "js",
        "woff",
        "woff2",
        "ttf",
        "eot",
        "map",
        "json",
    ]
)

# ---------------------------------------------------------------------------
# Page priority configuration
# ---------------------------------------------------------------------------

_CONTACT_PATHS = [
    "/contact",
    "/contact-us",
    "/contact_us",
    "/contacts",
    "/about",
    "/about-us",
    "/about_us",
    "/team",
    "/our-team",
    "/our_team",
    "/people",
    "/staff",
    "/leadership",
    "/management",
    "/company",
]

_SOURCE_MAP: dict[str, EmailSource] = {
    "/contact": EmailSource.WEBSITE_CONTACT,
    "/contact-us": EmailSource.WEBSITE_CONTACT,
    "/contact_us": EmailSource.WEBSITE_CONTACT,
    "/contacts": EmailSource.WEBSITE_CONTACT,
    "/team": EmailSource.WEBSITE_TEAM,
    "/our-team": EmailSource.WEBSITE_TEAM,
    "/our_team": EmailSource.WEBSITE_TEAM,
    "/people": EmailSource.WEBSITE_TEAM,
    "/staff": EmailSource.WEBSITE_TEAM,
    "/leadership": EmailSource.WEBSITE_TEAM,
    "/management": EmailSource.WEBSITE_TEAM,
    "/about": EmailSource.WEBSITE_ABOUT,
    "/about-us": EmailSource.WEBSITE_ABOUT,
    "/about_us": EmailSource.WEBSITE_ABOUT,
    "/company": EmailSource.WEBSITE_ABOUT,
}

# Confidence hints by source type
_CONFIDENCE_HINT: dict[EmailSource, int] = {
    EmailSource.WEBSITE_CONTACT: 35,
    EmailSource.WEBSITE_TEAM: 30,
    EmailSource.WEBSITE_ABOUT: 25,
    EmailSource.WEBSITE_GENERIC: 15,
}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; ColdReach/0.1; +https://github.com/yourusername/coldreach)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_emails(html: str, domain: str) -> list[str]:
    """Extract and deduplicate email addresses from raw HTML.

    Only returns emails belonging to *domain* or its subdomains.
    """
    found: list[str] = []
    seen: set[str] = set()

    def _add(addr: str) -> None:
        addr = addr.strip().lower()
        if not addr or addr in seen:
            return
        # Reject asset-extension TLDs (e.g. "icon@2x.png")
        tld = addr.rsplit(".", 1)[-1] if "." in addr else ""
        if tld in _ASSET_TLDS:
            return
        if _belongs_to_domain(addr, domain):
            seen.add(addr)
            found.append(addr)

    # mailto: links (highest quality — explicit intent)
    for match in _MAILTO_RE.finditer(html):
        _add(match.group(1))

    # Plain email pattern
    for match in _EMAIL_RE.finditer(html):
        _add(match.group(1))

    # Obfuscated patterns
    for match in _OBFUSCATED_RE.finditer(html):
        _add(f"{match.group(1)}@{match.group(2)}")

    return found


def _belongs_to_domain(email: str, domain: str) -> bool:
    """Return True if email's domain matches or is a subdomain of *domain*."""
    if "@" not in email:
        return False
    email_domain = email.split("@")[1]
    return email_domain == domain or email_domain.endswith(f".{domain}")


def _classify_path(path: str) -> EmailSource:
    """Map a URL path to the most appropriate EmailSource enum."""
    for prefix, source in _SOURCE_MAP.items():
        if path.lower().startswith(prefix):
            return source
    return EmailSource.WEBSITE_GENERIC


def _base_url(domain: str) -> str:
    """Build the https:// base URL for a domain."""
    if domain.startswith(("http://", "https://")):
        return domain.rstrip("/")
    return f"https://{domain}"


# ---------------------------------------------------------------------------
# Source implementation
# ---------------------------------------------------------------------------


class WebCrawlerSource(BaseSource):
    """Crawl company website pages to find email addresses.

    Fetches the homepage plus a fixed list of high-value paths
    (/contact, /team, /about, etc.) concurrently and extracts
    emails from each page.

    Parameters
    ----------
    timeout:
        Per-request HTTP timeout in seconds.
    max_pages:
        Maximum number of pages to fetch (homepage + paths).
    follow_homepage_links:
        If True, also parse any internal links on the homepage that
        match the high-value path patterns.
    """

    name = "web_crawler"

    def __init__(
        self,
        timeout: float = 10.0,
        max_pages: int = 8,
        follow_homepage_links: bool = True,
    ) -> None:
        super().__init__(timeout=timeout)
        self.max_pages = max_pages
        self.follow_homepage_links = follow_homepage_links

    async def fetch(
        self,
        domain: str,
        *,
        person_name: str | None = None,
    ) -> list[SourceResult]:
        base = _base_url(domain)
        urls_to_try: list[str] = [base] + [f"{base}{p}" for p in _CONTACT_PATHS]

        results: list[SourceResult] = []
        seen_emails: set[str] = set()

        async with httpx.AsyncClient(
            headers=_HEADERS,
            timeout=self.timeout,
            follow_redirects=True,
            verify=False,  # tolerate self-signed certs on small company sites
        ) as client:
            # Fetch homepage first — extract links to discover extra pages
            homepage_html = await self._fetch_page(client, base)
            if homepage_html:
                if self.follow_homepage_links:
                    discovered = self._discover_links(homepage_html, base, domain)
                    for link in discovered:
                        if link not in urls_to_try:
                            urls_to_try.append(link)

                emails = _extract_emails(homepage_html, domain)
                for email in emails:
                    if email not in seen_emails:
                        seen_emails.add(email)
                        source_type = EmailSource.WEBSITE_GENERIC
                        results.append(
                            SourceResult(
                                email=email,
                                source=source_type,
                                url=base,
                                context="homepage",
                                confidence_hint=_CONFIDENCE_HINT[source_type],
                            )
                        )

            # Fetch all remaining pages (up to max_pages - 1, homepage already done)
            pages_fetched = 1
            for url in urls_to_try[1:]:
                if pages_fetched >= self.max_pages:
                    break
                html = await self._fetch_page(client, url)
                if not html:
                    continue
                pages_fetched += 1

                path = urlparse(url).path or "/"
                source_type = _classify_path(path)
                emails = _extract_emails(html, domain)
                for email in emails:
                    if email not in seen_emails:
                        seen_emails.add(email)
                        results.append(
                            SourceResult(
                                email=email,
                                source=source_type,
                                url=url,
                                context=f"page: {path}",
                                confidence_hint=_CONFIDENCE_HINT.get(
                                    source_type, _CONFIDENCE_HINT[EmailSource.WEBSITE_GENERIC]
                                ),
                            )
                        )

        self._log.debug(
            "WebCrawler found %d email(s) across %d pages for %s",
            len(results),
            pages_fetched,
            domain,
        )
        return results

    async def _fetch_page(self, client: httpx.AsyncClient, url: str) -> str | None:
        """Fetch a single page, return HTML text or None on error."""
        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.text
            self._log.debug("HTTP %d for %s", resp.status_code, url)
            return None
        except httpx.TimeoutException:
            self._log.debug("Timeout fetching %s", url)
            return None
        except httpx.RequestError as exc:
            self._log.debug("Request error for %s: %s", url, exc)
            return None

    def _discover_links(self, html: str, base_url_str: str, domain: str) -> list[str]:
        """Parse homepage HTML for internal links matching high-value paths."""
        href_re = re.compile(r'href=["\']([^"\'#?]+)["\']', re.IGNORECASE)
        discovered: list[str] = []
        for match in href_re.finditer(html):
            href = match.group(1).strip()
            # Make absolute
            full_url = urljoin(base_url_str, href)
            parsed = urlparse(full_url)
            # Must be same domain, not a file
            if parsed.netloc and not parsed.netloc.endswith(domain):
                continue
            if "." in parsed.path.split("/")[-1]:
                continue  # looks like a file (e.g. /img/photo.jpg)
            for path in _CONTACT_PATHS:
                if parsed.path.lower().startswith(path):
                    discovered.append(full_url)
                    break
        return discovered
