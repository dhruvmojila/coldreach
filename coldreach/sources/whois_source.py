"""
WHOIS source — extract registrant/admin/tech contact emails from WHOIS records.

Uses python-whois (synchronous) run in an executor to avoid blocking the
event loop. WHOIS data often contains registrant email, admin email, and
tech contact email — these are high-value leads for small companies.

Note: Many large companies use privacy-protecting WHOIS proxies (e.g.
domains@squarespace.com). These are filtered out via a blocklist.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

import whois

from coldreach.core.models import EmailSource
from coldreach.sources.base import BaseSource, SourceResult

logger = logging.getLogger(__name__)

# Privacy-protection proxy patterns to discard
_PRIVACY_PATTERNS = re.compile(
    r"(privacy|proxy|whoisguard|protect|redacted|abuse|noreply|no-reply"
    r"|hostmaster|postmaster|webmaster|domains@|domain@)",
    re.IGNORECASE,
)


def _is_privacy_email(email: str) -> bool:
    return bool(_PRIVACY_PATTERNS.search(email))


def _extract_whois_emails(data: Any, domain: str) -> list[str]:
    """Pull all unique non-privacy emails from a whois result object."""
    raw_emails: list[str] = []

    # python-whois puts emails in data.emails (list or str)
    emails_field = getattr(data, "emails", None)
    if emails_field is None:
        return []
    if isinstance(emails_field, str):
        raw_emails = [emails_field]
    elif isinstance(emails_field, list):
        raw_emails = [str(e) for e in emails_field if e]

    seen: set[str] = set()
    result: list[str] = []
    for email in raw_emails:
        email = email.strip().lower()
        if not email or email in seen:
            continue
        if _is_privacy_email(email):
            continue
        # Only accept emails that look plausibly related to the domain
        # (registrant may use personal email — include those too)
        if "@" not in email:
            continue
        seen.add(email)
        result.append(email)

    return result


class WhoisSource(BaseSource):
    """Fetch WHOIS registrant contact emails for a domain.

    Parameters
    ----------
    timeout:
        Timeout passed to the thread executor (seconds).
    """

    name = "whois"

    async def fetch(
        self,
        domain: str,
        *,
        person_name: str | None = None,
    ) -> list[SourceResult]:
        loop = asyncio.get_event_loop()
        try:
            data = await asyncio.wait_for(
                loop.run_in_executor(None, whois.whois, domain),
                timeout=self.timeout,
            )
        except TimeoutError:
            self._log.debug("WHOIS timeout for %s", domain)
            return []
        except Exception as exc:
            self._log.debug("WHOIS error for %s: %s", domain, exc)
            return []

        emails = _extract_whois_emails(data, domain)
        if not emails:
            self._log.debug("WHOIS returned no usable emails for %s", domain)
            return []

        results = [
            SourceResult(
                email=email,
                source=EmailSource.WHOIS,
                url=f"whois:{domain}",
                context="WHOIS registrant/admin/tech contact",
                confidence_hint=20,
            )
            for email in emails
        ]
        self._log.debug("WHOIS found %d email(s) for %s", len(results), domain)
        return results
