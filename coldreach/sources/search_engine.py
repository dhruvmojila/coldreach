"""
Search engine source — queries SearXNG (self-hosted) for domain email mentions.

Fallback chain (in order):
  1. SearXNG local instance (http://localhost:8080 by default)
  2. DuckDuckGo Lite HTML (no JS, scrapeable, no auth)
  3. Brave Search API (free tier: 2000 req/month, requires API key)

Queries run against the target domain:
  - "@domain.com"                      — direct email format search
  - site:domain.com email contact      — on-site contact pages
  - "domain.com" email                 — general mentions

Rate limiting:
  - SearXNG: 1 req/3s per query (configurable)
  - DDG Lite: 1 req/5s (more aggressive block)
  - Brave: respects X-RateLimit-Remaining header

All results are filtered to emails belonging to the target domain.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

import httpx

from coldreach.core.models import EmailSource
from coldreach.sources.base import BaseSource, SourceResult

_EMAIL_RE = re.compile(
    r"([a-zA-Z0-9._%+\-]{1,64}@[a-zA-Z0-9.\-]{1,253}\.[a-zA-Z]{2,})",
    re.IGNORECASE,
)

_SEARXNG_DEFAULT = "http://localhost:8080"
_DDG_LITE_URL = "https://lite.duckduckgo.com/lite/"
_BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"

_HEADERS_BROWSER = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

_HEADERS_SEARXNG = {
    "User-Agent": "ColdReach/0.1",
    "Accept": "application/json",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_domain_emails(text: str, domain: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for m in _EMAIL_RE.finditer(text):
        email = m.group(1).strip().lower()
        if email in seen:
            continue
        if email.endswith(f"@{domain}") or email.endswith(f".{domain}"):
            seen.add(email)
            found.append(email)
    return found


def _build_queries(domain: str, person_name: str | None) -> list[str]:
    """Build targeted email-discovery queries for SearXNG.

    Avoids literal "@domain" queries — SearXNG search engines don't index
    the @ symbol and return 0 results.  Uses human-readable variants instead.
    """
    company = domain.split(".")[0]  # "snapdeal" from "snapdeal.com"
    queries = [
        f'"{domain}" email OR contact',  # domain + keywords → finds contact pages
        f'"{company}" contact email press',  # company name → PR/press contacts
        f"site:{domain} contact OR email OR press",  # indexed pages on domain
        f'"{company}" "email us" OR "contact us"',  # finds explicit email CTAs
    ]
    if person_name:
        queries.append(f'"{person_name}" "{domain}"')
    return queries


# ---------------------------------------------------------------------------
# SearXNG backend
# ---------------------------------------------------------------------------


async def _query_searxng(
    client: httpx.AsyncClient,
    base_url: str,
    query: str,
    domain: str,
) -> list[str]:
    """Query SearXNG and extract emails from snippets + crawl domain result URLs.

    Two-pass strategy:
    1. Fast: extract emails from result snippets/titles
    2. Deep: crawl result URLs that are on the target domain
       (contact pages, about pages, press pages)
    """
    try:
        resp = await client.get(
            f"{base_url.rstrip('/')}/search",
            params={"q": query, "format": "json", "categories": "general"},
        )
        if resp.status_code != 200:
            return []
        data: dict[str, Any] = resp.json()
        emails: list[str] = []
        crawl_urls: list[str] = []

        for result in data.get("results", []):
            # Pass 1: snippets
            for field in ("content", "title"):
                text = result.get(field, "") or ""
                emails.extend(_extract_domain_emails(str(text), domain))
            # Collect domain URLs for crawling
            url = result.get("url", "") or ""
            if domain in url:
                crawl_urls.append(url)

        # Pass 2: crawl target-domain pages found by SearXNG
        for url in crawl_urls[:3]:
            try:
                page = await client.get(
                    url,
                    timeout=8.0,
                    headers={"User-Agent": "Mozilla/5.0 (compatible; ColdReach/0.1)"},
                )
                if page.status_code == 200:
                    emails.extend(_extract_domain_emails(page.text, domain))
            except Exception:
                continue

        return emails
    except (httpx.RequestError, Exception):
        return []


# ---------------------------------------------------------------------------
# DuckDuckGo Lite fallback
# ---------------------------------------------------------------------------


async def _query_ddg_lite(
    client: httpx.AsyncClient,
    query: str,
    domain: str,
) -> list[str]:
    """Scrape DuckDuckGo Lite HTML for emails. Returns list of found emails."""
    try:
        resp = await client.post(
            _DDG_LITE_URL,
            data={"q": query},
            headers=_HEADERS_BROWSER,
        )
        if resp.status_code != 200:
            return []
        return _extract_domain_emails(resp.text, domain)
    except (httpx.RequestError, Exception):
        return []


# ---------------------------------------------------------------------------
# Brave Search API fallback
# ---------------------------------------------------------------------------


async def _query_brave(
    client: httpx.AsyncClient,
    api_key: str,
    query: str,
    domain: str,
) -> list[str]:
    """Query Brave Search API for emails."""
    try:
        resp = await client.get(
            _BRAVE_SEARCH_URL,
            params={"q": query, "count": 10},
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": api_key,
            },
        )
        if resp.status_code != 200:
            return []
        data: dict[str, Any] = resp.json()
        emails: list[str] = []
        for result in data.get("web", {}).get("results", []):
            for field in ("description", "title", "url"):
                text = result.get(field, "") or ""
                emails.extend(_extract_domain_emails(str(text), domain))
        return emails
    except (httpx.RequestError, Exception):
        return []


# ---------------------------------------------------------------------------
# Source implementation
# ---------------------------------------------------------------------------


class SearchEngineSource(BaseSource):
    """Search for domain email addresses via SearXNG → DDG Lite → Brave fallback chain.

    Parameters
    ----------
    searxng_url:
        URL of the local SearXNG instance. Set to None to skip SearXNG.
    brave_api_key:
        Brave Search API key (free: 2000 req/month). Set to None to skip.
    query_delay:
        Seconds to wait between queries to avoid rate limiting.
    timeout:
        Per-request HTTP timeout in seconds.
    """

    name = "search_engine"

    def __init__(
        self,
        searxng_url: str | None = _SEARXNG_DEFAULT,
        brave_api_key: str | None = None,
        query_delay: float = 3.0,
        timeout: float = 10.0,
    ) -> None:
        super().__init__(timeout=timeout)
        self.searxng_url = searxng_url
        self.brave_api_key = brave_api_key
        self.query_delay = query_delay

    async def fetch(
        self,
        domain: str,
        *,
        person_name: str | None = None,
    ) -> list[SourceResult]:
        queries = _build_queries(domain, person_name)
        seen_emails: set[str] = set()
        results: list[SourceResult] = []

        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
        ) as client:
            for i, query in enumerate(queries):
                if i > 0:
                    await asyncio.sleep(self.query_delay)

                emails = await self._run_query(client, query, domain)
                for email in emails:
                    if email not in seen_emails:
                        seen_emails.add(email)
                        results.append(
                            SourceResult(
                                email=email,
                                source=EmailSource.SEARXNG,
                                url="",
                                context=f"search: {query}",
                                confidence_hint=15,
                            )
                        )

        self._log.debug("SearchEngine found %d email(s) for %s", len(results), domain)
        return results

    async def _run_query(self, client: httpx.AsyncClient, query: str, domain: str) -> list[str]:
        """Try each backend in order, return first non-empty result."""
        # 1. SearXNG
        if self.searxng_url:
            emails = await _query_searxng(client, self.searxng_url, query, domain)
            if emails:
                self._log.debug("SearXNG returned %d email(s)", len(emails))
                return emails

        # 2. DuckDuckGo Lite
        emails = await _query_ddg_lite(client, query, domain)
        if emails:
            self._log.debug("DDG Lite returned %d email(s)", len(emails))
            return emails

        # 3. Brave Search API
        if self.brave_api_key:
            emails = await _query_brave(client, self.brave_api_key, query, domain)
            if emails:
                self._log.debug("Brave Search returned %d email(s)", len(emails))
                return emails

        return []
