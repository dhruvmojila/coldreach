"""
Async DNS / MX record checker.

Resolves MX records for an email's domain to confirm the domain is capable
of receiving email. This rules out typos, NXDOMAIN addresses, and domains
that have never been configured as mail receivers.

Uses dnspython's native async resolver (``dns.asyncresolver``) — no thread
pool hacks. Requires Python 3.11+ and dnspython >= 2.0.

Priority order of DNS checks
-----------------------------
1. MX records (primary — what mail servers accept for this domain?)
2. A record fallback (RFC 5321 §5: a domain with no MX but a valid A record
   is still technically a valid mail destination — we warn rather than fail)
"""

from __future__ import annotations

import logging

import dns.asyncresolver
import dns.exception
import dns.resolver

from coldreach.verify._types import CheckResult

logger = logging.getLogger(__name__)


async def get_mx_records(domain: str, timeout: float = 5.0) -> list[str]:
    """Resolve MX records for *domain*, sorted by priority (lowest first).

    Parameters
    ----------
    domain:
        The domain to look up (e.g. ``"stripe.com"``).
    timeout:
        DNS query timeout in seconds.

    Returns
    -------
    list[str]
        MX hostnames in priority order (lowest preference value first).
        Empty list if the domain has no MX records or does not exist.

    Examples
    --------
    >>> import asyncio
    >>> records = asyncio.run(get_mx_records("gmail.com"))
    >>> len(records) > 0
    True
    """
    resolver = dns.asyncresolver.Resolver()
    resolver.lifetime = timeout

    try:
        answers = await resolver.resolve(domain, "MX")
        sorted_records = sorted(
            [(int(rdata.preference), str(rdata.exchange).rstrip(".")) for rdata in answers],
            key=lambda x: x[0],
        )
        return [hostname for _, hostname in sorted_records]

    except dns.resolver.NXDOMAIN:
        logger.debug("DNS NXDOMAIN: domain %r does not exist", domain)
        return []

    except dns.resolver.NoAnswer:
        logger.debug("DNS NoAnswer: no MX records for %r", domain)
        return []

    except dns.exception.Timeout:
        logger.warning("DNS timeout for %r (%.1fs)", domain, timeout)
        return []

    except dns.exception.DNSException as exc:
        logger.warning("DNS error for %r: %s", domain, exc)
        return []


async def domain_exists(domain: str, timeout: float = 5.0) -> bool:
    """Return True if *domain* resolves to at least one A or AAAA record.

    Used as a fallback when no MX records are found — some small domains
    rely on the implicit MX → A record fallback defined in RFC 5321 §5.

    Parameters
    ----------
    domain:
        Domain name to check.
    timeout:
        DNS query timeout in seconds.
    """
    resolver = dns.asyncresolver.Resolver()
    resolver.lifetime = timeout

    for record_type in ("A", "AAAA"):
        try:
            await resolver.resolve(domain, record_type)
            return True
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
            continue
        except dns.exception.DNSException:
            continue

    return False


async def check_dns(email: str, timeout: float = 5.0) -> CheckResult:
    """Pipeline checker: verify the email's domain has a valid MX record.

    Scoring
    -------
    - MX records found:        +10 points
    - No MX but A record:      WARN, +0 points (RFC fallback, unusual)
    - NXDOMAIN / no A record:  FAIL, -30 points (domain does not exist)

    Parameters
    ----------
    email:
        Full email address string.
    timeout:
        DNS resolution timeout in seconds.

    Returns
    -------
    CheckResult
        PASS / WARN / FAIL as described above. PASS metadata includes
        ``mx_records`` (list of MX hostnames).

    Examples
    --------
    >>> import asyncio
    >>> result = asyncio.run(check_dns("test@gmail.com"))
    >>> result.passed
    True
    >>> "mx_records" in result.metadata
    True
    """
    if not email or "@" not in email:
        return CheckResult.fail(
            "Cannot extract domain — invalid email format",
            score_delta=-100,
        )

    try:
        domain = email.lower().split("@")[1]
    except IndexError:
        return CheckResult.fail(
            "No domain part found in email address",
            score_delta=-100,
        )

    if not domain or "." not in domain:
        return CheckResult.fail(
            f"Domain {domain!r} is not a valid FQDN",
            score_delta=-30,
            domain=domain,
        )

    mx_records = await get_mx_records(domain, timeout=timeout)

    if mx_records:
        logger.debug("MX records for %r: %s", domain, mx_records)
        return CheckResult.pass_(
            f"Found {len(mx_records)} MX record(s)",
            score_delta=10,
            domain=domain,
            mx_records=mx_records,
        )

    # No MX — try A/AAAA fallback (RFC 5321 §5)
    if await domain_exists(domain, timeout=timeout):
        logger.debug("No MX for %r, but A/AAAA record exists (RFC fallback)", domain)
        return CheckResult.warn(
            f"No MX records for {domain} — mail may use A record fallback (unusual)",
            score_delta=0,
            domain=domain,
            mx_records=[],
        )

    logger.debug("Domain %r does not exist (NXDOMAIN / no A record)", domain)
    return CheckResult.fail(
        f"Domain {domain!r} has no MX records and no A record — undeliverable",
        score_delta=-30,
        domain=domain,
        mx_records=[],
    )
