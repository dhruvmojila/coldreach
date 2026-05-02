"""
Company context fetcher for email personalization.

Scrapes the company's public pages and returns a structured summary that
Groq uses to personalize the cold email.  Designed to be fast — uses the
same httpx client patterns as WebCrawlerSource, no Playwright required.

Fallback chain:
  1. Scrape homepage + /about page via httpx (fast, works for 80% of sites)
  2. Use SearXNG meta-descriptions (works for JS-heavy SPAs)
  3. Return domain-only context if both fail (Groq still generates something)
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

_USER_AGENT = "Mozilla/5.0 (compatible; ColdReach/0.1; +https://github.com/dhruvmojila/coldreach)"
_HEADERS = {
    "User-Agent": _USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}
_SEARXNG_URL = "http://localhost:8088"


@dataclass
class CompanyContext:
    """Structured company context used for email personalization."""

    domain: str
    name: str
    description: str  # 1-3 sentences about what they do
    industry: str  # e.g. "fintech", "e-commerce", "SaaS"
    location: str  # e.g. "San Francisco, CA" or "India"
    recent_highlights: str  # recent news, milestones, or notable facts
    raw_text: str  # full scraped text for Groq to use directly

    def to_prompt_context(self) -> str:
        """Format context as a concise paragraph for Groq prompts."""
        parts = [f"{self.name} ({self.domain})"]
        if self.description:
            parts.append(self.description)
        if self.industry:
            parts.append(f"Industry: {self.industry}.")
        if self.location:
            parts.append(f"Location: {self.location}.")
        if self.recent_highlights:
            parts.append(self.recent_highlights)
        return " ".join(parts)[:1500]


async def get_company_context(
    domain: str,
    *,
    timeout: float = 10.0,
    max_chars: int = 2000,
    searxng_url: str = _SEARXNG_URL,
) -> CompanyContext:
    """Fetch and parse company context from their public pages.

    Parameters
    ----------
    domain:
        Company domain, e.g. ``"stripe.com"``.
    timeout:
        HTTP request timeout in seconds.
    max_chars:
        Maximum characters of raw text to keep for Groq context.
    searxng_url:
        Local SearXNG instance URL (fallback when httpx scrape fails).

    Returns
    -------
    CompanyContext
        Structured company context.  Always returns something — never raises.
    """
    raw = ""
    name = domain.split(".")[0].capitalize()

    async with httpx.AsyncClient(
        headers=_HEADERS,
        timeout=timeout,
        follow_redirects=True,
        verify=False,
    ) as client:
        # Try homepage + /about page
        for path in ["", "/about", "/about-us", "/company"]:
            url = f"https://{domain}{path}"
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    text = _strip_html(resp.text)
                    if len(text) > 200:
                        raw += text[:max_chars]
                        # Extract company name from <title> if possible
                        title_match = re.search(r"<title[^>]*>([^<]+)</title>", resp.text, re.I)
                        if title_match:
                            raw_title = title_match.group(1).strip()
                            # "Stripe | Financial Infrastructure" → "Stripe"
                            name = raw_title.split("|")[0].split("\u2013")[0].split("-")[0].strip()
                        break
            except Exception:
                continue

        # SearXNG fallback for JS-heavy SPAs
        if not raw:
            try:
                resp = await client.get(
                    f"{searxng_url}/search",
                    params={"q": f"site:{domain}", "format": "json"},
                    headers={"Accept": "application/json"},
                    timeout=8.0,
                )
                if resp.status_code == 200:
                    results = resp.json().get("results", [])
                    snippets = [r.get("content", "") for r in results[:4] if r.get("content")]
                    raw = " ".join(snippets)[:max_chars]
            except Exception:
                pass

    return _parse_context(domain, name, raw[:max_chars])


def _strip_html(html: str) -> str:
    """Remove HTML tags and collapse whitespace."""
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.I)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&[a-z]+;", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_context(domain: str, name: str, raw: str) -> CompanyContext:
    """Heuristically extract structured fields from raw page text."""
    text_lower = raw.lower()

    # Industry detection
    industry = ""
    industry_keywords = {
        "fintech": ["payment", "finance", "banking", "fintech", "wallet", "transaction"],
        "e-commerce": ["shop", "store", "retail", "marketplace", "product", "buy"],
        "SaaS": ["software", "platform", "saas", "cloud", "api", "developer"],
        "healthcare": ["health", "medical", "patient", "clinical", "pharma"],
        "edtech": ["education", "learning", "course", "student", "school"],
        "logistics": ["shipping", "delivery", "logistics", "supply chain", "freight"],
        "travel": ["travel", "flight", "hotel", "booking", "airline", "tour"],
    }
    for ind, keywords in industry_keywords.items():
        if any(kw in text_lower for kw in keywords):
            industry = ind
            break

    # Location heuristic — look for city/country mentions
    location = ""
    location_patterns = [
        r"(?:headquartered|based|founded)\s+in\s+([A-Z][a-zA-Z\s,]+?)(?:\.|,|\s+and)",
        r"([A-Z][a-z]+(?:,\s*[A-Z]{2})?),?\s+(?:USA|India|UK|Canada|Germany|Australia)",
    ]
    for pat in location_patterns:
        m = re.search(pat, raw)
        if m:
            location = m.group(1).strip()[:50]
            break

    # First 2-3 sentences as description
    sentences = re.split(r"(?<=[.!?])\s+", raw.strip())
    description = " ".join(sentences[:3])[:400] if sentences else ""

    return CompanyContext(
        domain=domain,
        name=name,
        description=description,
        industry=industry,
        location=location,
        recent_highlights="",
        raw_text=raw,
    )
