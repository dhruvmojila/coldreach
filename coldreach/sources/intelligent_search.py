"""
Intelligent search source — multi-stage email discovery.

Pipeline per domain:
  1. SearXNG → find company website + related pages
  2. Scrape top pages (httpx / Firecrawl if available)
  3. Groq → company summary + generate targeted search queries
  4. Run those queries through SearXNG + Reddit
  5. Extract domain emails from all results

Why this beats a simple "@domain.com" search:
  - Generic queries return off-topic results (adult sites, unrelated companies)
  - Company-aware queries like "fareleaders travel agency contact email India"
    are far more likely to find actual contact info
  - Groq identifies relevant Reddit communities for this specific company type
  - Multiple query angles: people, roles, events, press, partnerships

Requires: COLDREACH_GROQ_API_KEY in .env for query generation.
Falls back gracefully to smart heuristic queries without Groq.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Any

import httpx

from coldreach.core.models import EmailSource
from coldreach.sources.base import BaseSource, SourceResult

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(
    r"([a-zA-Z0-9][a-zA-Z0-9._%+\-]*@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})",
    re.IGNORECASE,
)
_SEARXNG_URL = os.getenv("COLDREACH_SEARXNG_URL", "http://localhost:8088")
_REDDIT_SEARCH = "https://www.reddit.com/search.json"
_GROQ_MODEL = "llama-3.1-8b-instant"  # fast + cheap

_SYSTEM_PROMPT = """\
You are an expert at finding contact emails for companies.
Given a company domain and context, you generate targeted search queries that \
will find email addresses, contact info, or people associated with the company.
Be specific. Use the company industry, location, and type in your queries.
Return ONLY the queries, one per line, no explanations."""

_QUERY_PROMPT = """\
Company domain: {domain}
Company context: {context}

Generate 6 search queries to find email addresses for this company.
Mix these angles:
1. Direct email format: "@{domain}"
2. Company + role: "CEO OR HR OR partnerships {domain}"
3. Reddit-style: company name + industry + contact
4. Press/media: company name + interview OR announcement + email
5. Job/career: company + jobs OR careers + email
6. Industry community: company name + relevant forum/community + contact

Return exactly 6 queries, one per line."""

_REDDIT_PROMPT = """\
Company domain: {domain}
Company context: {context}

Name 4 subreddits where this company or its industry would be discussed.
Return only subreddit names (without r/), one per line.
Choose communities where the company might be mentioned with contact details."""


def _extract_domain_emails(text: str, domain: str) -> list[str]:
    """Extract emails belonging to *domain* from *text*."""
    seen: set[str] = set()
    result: list[str] = []
    for m in _EMAIL_RE.finditer(text):
        email = m.group(1).strip().lower()
        if email in seen:
            continue
        d = email.split("@")[1] if "@" in email else ""
        if d == domain or d.endswith(f".{domain}"):
            seen.add(email)
            result.append(email)
    return result


class IntelligentSearchSource(BaseSource):
    """Multi-stage email discovery: SearXNG → Firecrawl → Groq → targeted queries.

    Parameters
    ----------
    groq_api_key:
        Groq API key.  Falls back to ``COLDREACH_GROQ_API_KEY`` env var.
        Without Groq, uses heuristic queries (still better than generic).
    searxng_url:
        Local SearXNG instance.
    timeout:
        Per-request HTTP timeout.
    """

    name = "intelligent_search"

    def __init__(
        self,
        groq_api_key: str | None = None,
        searxng_url: str = _SEARXNG_URL,
        timeout: float = 20.0,
    ) -> None:
        super().__init__(timeout=timeout)
        # Load Groq key from pydantic-settings config (reads .env) if not provided
        if groq_api_key:
            self.groq_api_key = groq_api_key
        else:
            try:
                from coldreach.config import get_settings

                self.groq_api_key = get_settings().groq_api_key
            except Exception:
                self.groq_api_key = os.getenv("COLDREACH_GROQ_API_KEY")
        self.searxng_url = searxng_url.rstrip("/")

    async def fetch(
        self,
        domain: str,
        *,
        person_name: str | None = None,
    ) -> list[SourceResult]:
        seen: set[str] = set()
        results: list[SourceResult] = []

        def _add(email: str, ctx: str) -> None:
            e = email.lower().strip()
            if e not in seen:
                seen.add(e)
                results.append(
                    SourceResult(
                        email=e,
                        source=EmailSource.SEARXNG,
                        url="",
                        context=ctx,
                        confidence_hint=20,
                    )
                )

        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            headers={"User-Agent": "ColdReach/0.1 (email discovery)"},
        ) as client:
            # ── Step 1: Get company context by scraping their site ────────────
            context = await self._get_company_context(client, domain)
            self._log.debug("Company context for %s: %s", domain, context[:200])

            # ── Step 2: Generate targeted queries (Groq or heuristic) ─────────
            queries = await self._generate_queries(domain, context, person_name)
            reddit_subs = await self._generate_reddit_subs(domain, context)
            self._log.info(
                "intelligent_search: %d queries + %d subreddits for %s",
                len(queries),
                len(reddit_subs),
                domain,
            )

            # ── Step 3: Run queries concurrently ──────────────────────────────
            tasks: list[Any] = []
            for query in queries:
                tasks.append(self._searxng_query(client, query, domain))
            for sub in reddit_subs:
                tasks.append(self._reddit_search(client, sub, domain))

            batches = await asyncio.gather(*tasks, return_exceptions=True)
            for batch in batches:
                if isinstance(batch, (Exception, BaseException)):
                    self._log.debug("intelligent_search subtask error: %s", batch)
                    continue
                if not isinstance(batch, list):
                    continue
                for email, ctx in batch:
                    _add(email, ctx)

        self._log.info("intelligent_search: found %d email(s) for %s", len(results), domain)
        return results

    # ── Company context ────────────────────────────────────────────────────────

    async def _get_company_context(self, client: httpx.AsyncClient, domain: str) -> str:
        """Get company context from SearXNG snippets (reliable even for SPAs).

        SearXNG returns meta descriptions pre-rendered by search engines,
        so this works even when the company site is a JS-heavy SPA.
        """
        # Primary: SearXNG meta descriptions (search-engine rendered, works for SPAs)
        try:
            resp = await client.get(
                f"{self.searxng_url}/search",
                params={"q": f"site:{domain}", "format": "json"},
                headers={"Accept": "application/json"},
                timeout=10.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                snippets = [
                    r.get(field) or ""
                    for r in data.get("results", [])[:5]
                    for field in ("content", "title")
                    if r.get(field) and len(r.get(field, "")) > 20
                ]
                if snippets:
                    return " | ".join(snippets[:5])[:2000]
        except Exception:
            pass

        # Fallback: scrape homepage (works for server-rendered sites)
        for url in [f"https://{domain}", f"https://www.{domain}"]:
            try:
                resp = await client.get(url, timeout=8.0)
                if resp.status_code == 200:
                    text = _strip_html(resp.text)
                    # Skip if mostly JavaScript
                    if len(text) > 200 and "function" not in text[:80]:
                        return text[:2000]
            except Exception:
                continue

        return f"Company website: {domain}"

    # ── Query generation ───────────────────────────────────────────────────────

    async def _generate_queries(
        self,
        domain: str,
        context: str,
        person_name: str | None,
    ) -> list[str]:
        """Return targeted search queries, using Groq if available."""
        if self.groq_api_key:
            try:
                queries = await asyncio.to_thread(self._groq_queries, domain, context)
                if queries:
                    if person_name:
                        queries.append(f'"{person_name}" "{domain}" email')
                    return queries[:7]
            except Exception as exc:
                self._log.debug("Groq query generation failed: %s", exc)

        # Heuristic fallback — better than a single generic query
        company = domain.split(".")[0].capitalize()
        base = [
            f'"@{domain}"',
            f'"{company}" email OR contact',
            f'"{domain}" email contact',
            f'"{company}" CEO OR founder OR HR email',
            f"site:{domain} contact OR email",
        ]
        if person_name:
            base.append(f'"{person_name}" "{domain}"')
        return base

    async def _generate_reddit_subs(self, domain: str, context: str) -> list[str]:
        """Return relevant subreddits using Groq, or sensible defaults."""
        if self.groq_api_key:
            try:
                subs = await asyncio.to_thread(self._groq_reddit_subs, domain, context)
                if subs:
                    return subs[:4]
            except Exception as exc:
                self._log.debug("Groq Reddit sub generation failed: %s", exc)
        # Default: search the domain in a few broad communities
        return [f'"{domain}"', f'"{domain.split(".")[0]}"']

    def _groq_queries(self, domain: str, context: str) -> list[str]:
        """Blocking Groq call — run in thread via asyncio.to_thread."""
        from groq import Groq  # lazy import

        client = Groq(api_key=self.groq_api_key)
        resp = client.chat.completions.create(
            model=_GROQ_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": _QUERY_PROMPT.format(domain=domain, context=context[:1000]),
                },
            ],
            max_tokens=300,
            temperature=0.3,
        )
        raw = resp.choices[0].message.content or ""
        return [q.strip() for q in raw.splitlines() if q.strip() and "@" not in q[:5]]

    def _groq_reddit_subs(self, domain: str, context: str) -> list[str]:
        """Blocking Groq call for subreddit names."""
        from groq import Groq

        client = Groq(api_key=self.groq_api_key)
        resp = client.chat.completions.create(
            model=_GROQ_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": _REDDIT_PROMPT.format(domain=domain, context=context[:800]),
                },
            ],
            max_tokens=100,
            temperature=0.2,
        )
        raw = resp.choices[0].message.content or ""
        return [s.strip().lstrip("r/").lstrip("/") for s in raw.splitlines() if s.strip()]

    # ── Search backends ────────────────────────────────────────────────────────

    async def _searxng_query(
        self,
        client: httpx.AsyncClient,
        query: str,
        domain: str,
    ) -> list[tuple[str, str]]:
        """Run one SearXNG query and extract domain emails from results."""
        results: list[tuple[str, str]] = []
        try:
            resp = await client.get(
                f"{self.searxng_url}/search",
                params={"q": query, "format": "json", "categories": "general"},
                headers={"Accept": "application/json"},
                timeout=15.0,
            )
            if resp.status_code != 200:
                return results
            data: dict[str, Any] = resp.json()
            for r in data.get("results", []):
                for field in ("content", "title", "url"):
                    text = r.get(field, "") or ""
                    for email in _extract_domain_emails(str(text), domain):
                        results.append((email, f"searxng: {query[:50]}"))
        except Exception as exc:
            self._log.debug("SearXNG query %r failed: %s", query, exc)
        return results

    async def _reddit_search(
        self,
        client: httpx.AsyncClient,
        sub_or_query: str,
        domain: str,
    ) -> list[tuple[str, str]]:
        """Search Reddit for a subreddit or query term, extract emails."""
        results: list[tuple[str, str]] = []
        try:
            resp = await client.get(
                _REDDIT_SEARCH,
                params={
                    "q": sub_or_query if domain in sub_or_query else f'"{domain}" {sub_or_query}',
                    "sort": "relevance",
                    "limit": 25,
                    "type": "link",
                },
                headers={"User-Agent": "ColdReach/0.1 (email discovery)"},
                timeout=15.0,
            )
            if resp.status_code != 200:
                return results
            data: dict[str, Any] = resp.json()
            for post in data.get("data", {}).get("children", []):
                pd = post.get("data", {})
                text = f"{pd.get('title', '')} {pd.get('selftext', '')}"
                for email in _extract_domain_emails(text, domain):
                    results.append((email, f"reddit: {sub_or_query[:40]}"))
        except Exception as exc:
            self._log.debug("Reddit search %r failed: %s", sub_or_query, exc)
        return results


def _strip_html(html: str) -> str:
    """Remove HTML tags and collapse whitespace."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&[a-z]+;", " ", text)
    return re.sub(r"\s+", " ", text).strip()
