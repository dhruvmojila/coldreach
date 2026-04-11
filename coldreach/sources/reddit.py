"""
Reddit source — search Reddit posts/comments for company contact emails.

Uses the public Reddit JSON API — no authentication required.
Rate limit: 1 request per second (enforced via asyncio.sleep).

Queries:
  1. Search for "@domain.com" mentions across all of Reddit
  2. Search for "company name" + "email" or "contact"

Both queries parse post titles, selftext, and comment bodies for
email patterns matching the target domain.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

import httpx

from coldreach.core.models import EmailSource
from coldreach.sources.base import BaseSource, SourceResult

_REDDIT_SEARCH = "https://www.reddit.com/search.json"
_HEADERS = {
    "User-Agent": "ColdReach/0.1 (contact finder; +https://github.com/yourusername/coldreach)",
    "Accept": "application/json",
}

_EMAIL_RE = re.compile(
    r"([a-zA-Z0-9._%+\-]{1,64}@[a-zA-Z0-9.\-]{1,253}\.[a-zA-Z]{2,})",
    re.IGNORECASE,
)


def _extract_domain_emails(text: str, domain: str) -> list[str]:
    """Extract emails belonging to *domain* from *text*."""
    found: list[str] = []
    seen: set[str] = set()
    for match in _EMAIL_RE.finditer(text):
        email = match.group(1).strip().lower()
        if email in seen:
            continue
        if email.endswith(f"@{domain}") or email.endswith(f".{domain}"):
            seen.add(email)
            found.append(email)
    return found


class RedditSource(BaseSource):
    """Search Reddit for company email addresses via the public JSON API.

    Parameters
    ----------
    timeout:
        Per-request HTTP timeout in seconds.
    max_results:
        Maximum number of Reddit posts to inspect per query.
    """

    name = "reddit"

    def __init__(self, timeout: float = 10.0, max_results: int = 25) -> None:
        super().__init__(timeout=timeout)
        self.max_results = max_results

    async def fetch(
        self,
        domain: str,
        *,
        person_name: str | None = None,
    ) -> list[SourceResult]:
        queries = [f'"{domain}"']
        if person_name:
            queries.append(f'"{person_name}" "{domain}"')

        results: list[SourceResult] = []
        seen_emails: set[str] = set()

        async with httpx.AsyncClient(
            headers=_HEADERS,
            timeout=self.timeout,
            follow_redirects=True,
        ) as client:
            for i, query in enumerate(queries):
                if i > 0:
                    await asyncio.sleep(1.0)  # 1 req/s rate limit
                posts = await self._search(client, query)
                for post in posts:
                    texts = self._extract_texts(post)
                    for text in texts:
                        for email in _extract_domain_emails(text, domain):
                            if email not in seen_emails:
                                seen_emails.add(email)
                                post_url = post.get("url", "")
                                results.append(
                                    SourceResult(
                                        email=email,
                                        source=EmailSource.REDDIT,
                                        url=str(post_url),
                                        context=f"Reddit post: {post.get('title', '')}",
                                        confidence_hint=15,
                                    )
                                )

        self._log.debug("Reddit found %d email(s) for %s", len(results), domain)
        return results

    async def _search(self, client: httpx.AsyncClient, query: str) -> list[dict[str, Any]]:
        """Run a Reddit search and return the list of post data dicts."""
        try:
            resp = await client.get(
                _REDDIT_SEARCH,
                params={"q": query, "sort": "new", "limit": self.max_results, "type": "link"},
            )
            if resp.status_code != 200:
                self._log.debug("Reddit search HTTP %d for query %r", resp.status_code, query)
                return []
            data = resp.json()
            posts = data.get("data", {}).get("children", [])
            return [p.get("data", {}) for p in posts]
        except httpx.RequestError as exc:
            self._log.debug("Reddit request error: %s", exc)
            return []

    def _extract_texts(self, post: dict[str, Any]) -> list[str]:
        """Pull all text content from a post data dict."""
        texts: list[str] = []
        for key in ("title", "selftext", "url"):
            val = post.get(key)
            if isinstance(val, str) and val:
                texts.append(val)
        return texts
