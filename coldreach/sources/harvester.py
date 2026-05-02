"""
theHarvester source — HTTP REST API client.

The ``coldreach-theharvester`` Docker container runs ``restfulHarvest``,
which exposes a REST API on port 5050.  We call it directly with httpx
instead of docker exec (which failed silently because the container's
entrypoint is the API server, not the CLI).

API endpoint:
    GET http://localhost:5050/query
    ?domain=acme.com&source=duckduckgo,bing,crtsh&limit=500

Swagger docs (when container is running):
    http://localhost:5050/docs

Response JSON:
    {
      "emails": ["user@acme.com", ...],
      "hosts": [...],
      "interesting_urls": [...],
      ...
    }

Free sources (no API key needed):
    duckduckgo, yahoo, bing, baidu, crtsh, certspotter,
    hackertarget, rapiddns, dnsdumpster, urlscan, otx, robtex

Excluded (slow / decommissioned):
    commoncrawl   — terabyte dataset, queries take 10+ minutes
    waybackarchive — rarely contains emails, very slow
    thc            — unreliable timeouts
    threatcrowd    — decommissioned

Service: docker compose up theharvester
"""

from __future__ import annotations

import logging
import re

import httpx

from coldreach.core.models import EmailSource
from coldreach.sources.base import BaseSource, SourceResult

logger = logging.getLogger(__name__)

_API_BASE = "http://localhost:5050"

# Free sources validated against the actual API's supported source list.
# 'bing' is NOT a valid source name — use 'duckduckgo', 'yahoo', 'baidu'.
# Each name is passed as a separate 'source' query param (the API expects
# source: array, not a comma-joined string).
_FREE_SOURCES = [
    "duckduckgo",
    "yahoo",
    "baidu",
    "crtsh",
    "certspotter",
    "hackertarget",
    "rapiddns",
    "dnsdumpster",
    "urlscan",
    "otx",
    "robtex",
]

# Regex: valid RFC-ish email local+domain
_VALID_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]{1,64}@[a-zA-Z0-9.\-]{1,253}\.[a-zA-Z]{2,}$")

# Reject HTML-escaped artifacts like "u003caccount@domain.com"
_HTML_ENTITY_PREFIX_RE = re.compile(r"^u[0-9a-f]{3,4}", re.IGNORECASE)


class HarvesterSource(BaseSource):
    """Discover emails via the theHarvester REST API (localhost:5050).

    Calls ``GET /query?domain=...&source=...&limit=...`` on the running
    ``coldreach-theharvester`` container.  No docker exec needed — the
    container's REST server is the correct integration point.

    Parameters
    ----------
    api_base:
        Base URL of the theHarvester REST server.
    sources:
        Comma-separated source names.  Defaults to all free sources.
    limit:
        Maximum results per source query.
    timeout:
        HTTP request timeout in seconds.  theHarvester queries several
        external APIs so allow generous time.
    """

    name = "theharvester"

    def __init__(
        self,
        api_base: str = _API_BASE,
        sources: str | None = None,
        limit: int = 500,
        timeout: float = 240.0,
        # Kept for compatibility with FinderConfig.harvester_container
        container: str = "coldreach-theharvester",
        max_wait: float = 240.0,
        harvester_sources: str | None = None,
    ) -> None:
        super().__init__(timeout=timeout)
        self.api_base = api_base.rstrip("/")
        self.sources = sources or harvester_sources or ",".join(_FREE_SOURCES)
        self.limit = limit

    async def fetch(
        self,
        domain: str,
        *,
        person_name: str | None = None,
    ) -> list[SourceResult]:
        emails = await self._query_api(domain)
        self._log.debug("theHarvester found %d email(s) for %s", len(emails), domain)
        return [
            SourceResult(
                email=email,
                source=EmailSource.THE_HARVESTER,
                url=self.api_base,
                context=f"theHarvester REST API scan of {domain}",
                confidence_hint=20,
            )
            for email in emails
        ]

    async def _query_api(self, domain: str) -> list[str]:
        """Call GET /query and parse the email list from the response.

        The API requires ``source`` as a repeated query parameter
        (source=X&source=Y), not as a single comma-separated string.
        httpx encodes list values correctly when passed as a list.
        """
        # Split comma-joined string into individual sources for the API
        source_list = [s.strip() for s in self.sources.split(",") if s.strip()]

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(
                    f"{self.api_base}/query",
                    params=[
                        ("domain", domain),
                        *[("source", s) for s in source_list],
                        ("limit", str(self.limit)),
                    ],
                )
        except httpx.ConnectError:
            self._log.debug(
                "theHarvester: cannot connect to %s — is the container running?",
                self.api_base,
            )
            return []
        except httpx.TimeoutException:
            self._log.warning(
                "theHarvester: request timed out after %ss for %s",
                self.timeout,
                domain,
            )
            return []
        except httpx.RequestError as exc:
            self._log.debug("theHarvester: request error: %s", exc)
            return []

        if resp.status_code != 200:
            self._log.debug("theHarvester: HTTP %d for %s", resp.status_code, domain)
            return []

        try:
            data = resp.json()
        except Exception:
            self._log.debug("theHarvester: invalid JSON response")
            return []

        raw_emails: list[str] = data.get("emails") or []
        return self._filter_emails(raw_emails, domain)

    def _filter_emails(self, raw: list[str], domain: str) -> list[str]:
        """Normalise, domain-filter, and deduplicate email list."""
        domain_lower = domain.lower()
        seen: set[str] = set()
        result: list[str] = []

        for email in raw:
            email = email.strip().lower()
            if not email or email in seen:
                continue
            if not _VALID_EMAIL_RE.match(email):
                continue
            local = email.split("@")[0]
            if _HTML_ENTITY_PREFIX_RE.match(local):
                continue
            if not (email.endswith(f"@{domain_lower}") or email.endswith(f".{domain_lower}")):
                continue
            seen.add(email)
            result.append(email)

        return result
