"""
Company name → primary domain resolver.

Strategy (tried in order, stops on first success):
    1. Clearbit Autocomplete API — free, no key, highly reliable for known companies.
       Endpoint: https://autocomplete.clearbit.com/v1/companies/suggest?query=<name>
    2. DuckDuckGo Lite search — fallback for companies not in Clearbit's index.
       Parses the first organic result URL for the domain.

Neither endpoint requires authentication.  Both are rate-limited by IP but
casual use (a few lookups per minute) is well within limits.

Returns None if the domain cannot be resolved rather than raising.
"""

from __future__ import annotations

import logging
import re

import httpx

logger = logging.getLogger(__name__)

_CLEARBIT_URL = "https://autocomplete.clearbit.com/v1/companies/suggest"
_DDG_URL = "https://duckduckgo.com/lite/"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; ColdReach/0.1; +https://github.com/dhruvmojila/coldreach)"
    ),
    "Accept": "application/json",
}

# Domains to reject as "company website" candidates
_NOISE_DOMAINS = frozenset(
    [
        "linkedin.com",
        "twitter.com",
        "x.com",
        "facebook.com",
        "instagram.com",
        "youtube.com",
        "wikipedia.org",
        "bloomberg.com",
        "crunchbase.com",
        "pitchbook.com",
        "glassdoor.com",
        "indeed.com",
        "reddit.com",
        "github.com",
        "medium.com",
        "techchrunch.com",
        "forbes.com",
        "reuters.com",
    ]
)


async def resolve_domain(
    company_name: str,
    *,
    timeout: float = 10.0,
) -> str | None:
    """Resolve a company name to its primary domain.

    Parameters
    ----------
    company_name:
        Human-readable company name, e.g. ``"Stripe"`` or ``"Acme Corp"``.
    timeout:
        HTTP request timeout in seconds.

    Returns
    -------
    str or None
        Bare domain string (e.g. ``"stripe.com"``), or ``None`` if
        resolution fails.

    Examples
    --------
    >>> import asyncio
    >>> asyncio.run(resolve_domain("Stripe"))
    'stripe.com'
    """
    if not company_name or not company_name.strip():
        return None

    name = company_name.strip()

    async with httpx.AsyncClient(
        headers=_HEADERS, timeout=timeout, follow_redirects=True
    ) as client:
        domain = await _try_clearbit(client, name)
        if domain:
            logger.debug("Clearbit resolved %r → %s", name, domain)
            return domain

        domain = await _try_ddg(client, name)
        if domain:
            logger.debug("DDG resolved %r → %s", name, domain)
            return domain

    logger.warning("Could not resolve domain for company: %r", name)
    return None


async def _try_clearbit(client: httpx.AsyncClient, name: str) -> str | None:
    """Query Clearbit Autocomplete for the company domain."""
    try:
        resp = await client.get(_CLEARBIT_URL, params={"query": name})
        if resp.status_code != 200:
            return None
        results: list[dict[str, object]] = resp.json()
        if results:
            domain = str(results[0].get("domain", ""))
            return domain.lower().strip() or None
    except Exception as exc:
        logger.debug("Clearbit lookup failed for %r: %s", name, exc)
    return None


async def _try_ddg(client: httpx.AsyncClient, name: str) -> str | None:
    """Search DuckDuckGo Lite and extract domain from first result URL."""
    try:
        resp = await client.post(
            _DDG_URL,
            data={"q": f"{name} official website", "kl": "us-en"},
            headers={
                **_HEADERS,
                "Accept": "text/html",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        if resp.status_code != 200:
            return None
        return _extract_domain_from_ddg_html(resp.text)
    except Exception as exc:
        logger.debug("DDG lookup failed for %r: %s", name, exc)
    return None


def _extract_domain_from_ddg_html(html: str) -> str | None:
    """Parse DuckDuckGo Lite HTML and return the domain of the first organic result."""
    # DDG Lite result links look like: <a class="result-link" href="https://stripe.com/...">
    href_re = re.compile(r'href=["\']https?://([^/"\']+)', re.IGNORECASE)
    for match in href_re.finditer(html):
        raw = match.group(1).lower()
        # Strip www. prefix
        domain = raw.removeprefix("www.")
        # Skip DDG internal pages and known noise
        if "duckduckgo.com" in domain:
            continue
        if domain in _NOISE_DOMAINS:
            continue
        # Must look like a valid domain (at least one dot, no path separators)
        if "." in domain and "/" not in domain:
            return domain
    return None
