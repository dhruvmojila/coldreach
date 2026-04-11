"""
Catch-all domain detection.

A "catch-all" mail server accepts RCPT TO for ANY address at the domain —
including completely random ones. This makes SMTP verification useless
for individual addresses.

Detection method:
  Ask Reacher to verify a randomly-generated address at the domain.
  If it comes back "deliverable", the domain is catch-all.

  Fallback (no Reacher): always returns UNKNOWN — we can't detect
  catch-all without sending an actual SMTP probe.

Result is cached per domain for the session to avoid redundant probes.
"""

from __future__ import annotations

import logging
import secrets
import string

from coldreach.verify._types import CheckResult

logger = logging.getLogger(__name__)

# Module-level cache: domain → is_catch_all (True/False/None=unknown)
_cache: dict[str, bool | None] = {}


def _random_local(length: int = 20) -> str:
    """Generate a random string that is extremely unlikely to be a real address."""
    alphabet = string.ascii_lowercase + string.digits
    return "cr-probe-" + "".join(secrets.choice(alphabet) for _ in range(length))


async def check_catchall(
    domain: str,
    *,
    reacher_url: str | None = None,
    timeout: float = 10.0,
) -> CheckResult:
    """Probe the domain to detect catch-all behaviour.

    Parameters
    ----------
    domain:
        The domain to probe (e.g. ``"stripe.com"``).
    reacher_url:
        Base URL of the Reacher microservice. If None, returns SKIP.
    timeout:
        HTTP timeout for the Reacher request.

    Returns
    -------
    CheckResult
        - PASS (score_delta=0): domain is NOT catch-all
        - FAIL (score_delta=-40): domain IS catch-all
        - SKIP: Reacher not configured
        - WARN: probe was inconclusive
    """
    if not domain:
        return CheckResult.fail("Empty domain", score_delta=-10)

    # Return cached result immediately
    if domain in _cache:
        cached = _cache[domain]
        if cached is True:
            return CheckResult.fail(
                f"{domain} is a catch-all domain",
                score_delta=-40,
                is_catch_all=True,
            )
        if cached is False:
            return CheckResult.pass_(score_delta=0)
        return CheckResult.skip("Catch-all status unknown (cached)")

    if not reacher_url:
        return CheckResult.skip("Reacher not configured — catch-all unknown")

    probe_email = f"{_random_local()}@{domain}"
    result = await _probe_via_reacher(probe_email, reacher_url, timeout)
    _cache[domain] = result
    logger.debug("Catch-all probe for %s: %s", domain, result)

    if result is True:
        return CheckResult.fail(
            f"{domain} is a catch-all domain",
            score_delta=-40,
            is_catch_all=True,
        )
    if result is False:
        return CheckResult.pass_(score_delta=0)
    return CheckResult.skip("Catch-all probe inconclusive")


async def is_catch_all(
    domain: str,
    *,
    reacher_url: str | None = None,
    timeout: float = 10.0,
) -> bool | None:
    """Return True/False/None for catch-all status.

    Convenience wrapper around :func:`check_catchall` that returns a
    plain boolean (or None if unknown) rather than a CheckResult.
    """
    result = await check_catchall(domain, reacher_url=reacher_url, timeout=timeout)
    if result.passed:
        return False
    meta = result.metadata.get("is_catch_all")
    if meta is True:
        return True
    return None


async def _probe_via_reacher(
    email: str,
    reacher_url: str,
    timeout: float,
) -> bool | None:
    """Send a probe to Reacher. Returns True=catch-all, False=not, None=unknown."""
    import httpx  # local import to keep module lightweight

    url = f"{reacher_url.rstrip('/')}/v0/check_email"
    payload = {"to_email": email}

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload)
        if resp.status_code != 200:
            return None
        data = resp.json()
        smtp = data.get("smtp") or {}
        # Reacher reports catch-all in smtp.is_catch_all
        catch_all_flag = smtp.get("is_catch_all")
        if catch_all_flag is True:
            return True
        # If probe says deliverable but it's a random address → catch-all
        is_deliverable = smtp.get("can_connect_smtp") and smtp.get("is_deliverable")
        return bool(is_deliverable)
    except Exception:
        return None


def clear_cache() -> None:
    """Clear the in-memory catch-all cache (useful in tests)."""
    _cache.clear()
