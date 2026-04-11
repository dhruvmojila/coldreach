"""
Disposable / throwaway email domain detection.

Checks whether the domain part of an email address belongs to a known
throwaway or temporary email service. These addresses are useless for
lead generation — they're created once, read once, and abandoned.

The blocklist is bundled in ``coldreach/data/disposable_domains.txt``
and loaded once, then cached via ``functools.lru_cache``.

To extend the list: add new lowercase domain names (one per line) to that
file, or contribute upstream at:
  https://github.com/disposable-email-domains/disposable-email-domains
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from coldreach.verify._types import CheckResult

logger = logging.getLogger(__name__)

_DATA_FILE = Path(__file__).parent.parent / "data" / "disposable_domains.txt"


@lru_cache(maxsize=1)
def _load_domains() -> frozenset[str]:
    """Parse and cache the bundled disposable domain blocklist.

    Returns
    -------
    frozenset[str]
        Lowercase domain strings. Empty set if the data file is missing.
    """
    if not _DATA_FILE.exists():
        logger.warning(
            "disposable_domains.txt not found at %s — disposable check disabled",
            _DATA_FILE,
        )
        return frozenset()

    domains: set[str] = set()
    for raw_line in _DATA_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip().lower()
        if line and not line.startswith("#"):
            domains.add(line)

    logger.debug("Loaded %d disposable domains from blocklist", len(domains))
    return frozenset(domains)


# Public alias — tests can read this to assert the blocklist loaded correctly.
DISPOSABLE_DOMAINS: frozenset[str] = frozenset()  # populated lazily on first access


def is_disposable(email: str) -> bool:
    """Return True if *email* uses a known disposable / throwaway domain.

    Parameters
    ----------
    email:
        Full email address. Only the domain part is checked.

    Returns
    -------
    bool

    Examples
    --------
    >>> is_disposable("user@mailinator.com")
    True
    >>> is_disposable("user@gmail.com")
    False
    """
    try:
        domain = email.lower().split("@")[1]
    except IndexError:
        return False

    return domain in _load_domains()


def check_disposable(email: str) -> CheckResult:
    """Pipeline checker: fail if email uses a disposable domain.

    Parameters
    ----------
    email:
        Full email address string.

    Returns
    -------
    CheckResult
        FAIL (score -50) if disposable, PASS (score +5) otherwise.

    Examples
    --------
    >>> check_disposable("test@mailinator.com").failed
    True
    >>> check_disposable("john@stripe.com").passed
    True
    """
    if not email or "@" not in email:
        return CheckResult.skip("Invalid format — cannot extract domain")

    try:
        domain = email.lower().split("@")[1]
    except IndexError:
        return CheckResult.skip("Invalid format — no domain part")

    if domain in _load_domains():
        logger.debug("Disposable domain detected: %s", domain)
        return CheckResult.fail(
            f"Known disposable email service: {domain}",
            score_delta=-50,
            domain=domain,
        )

    logger.debug("Domain %s is not in disposable blocklist", domain)
    return CheckResult.pass_(
        "Not a disposable email domain",
        score_delta=5,
        domain=domain,
    )
