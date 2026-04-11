"""
Email syntax validation (RFC 5321 / 5322).

Uses the ``email-validator`` library which implements the full RFC spec,
including international domain names (IDN), quoted local parts, IP address
domains, and correct normalisation (lowercase domain, Unicode NFC).

This is the first and fastest check in the pipeline — pure CPU, no network.
"""

from __future__ import annotations

import logging

from email_validator import EmailNotValidError, validate_email

from coldreach.verify._types import CheckResult

logger = logging.getLogger(__name__)


def check_syntax(email: str) -> CheckResult:
    """Validate an email address against RFC 5322 syntax rules.

    Does **not** check whether the mailbox actually exists — this is a
    structural check only.

    On success the ``metadata`` dict contains:
    - ``"normalized"``: the RFC-normalised form of the address (lowercase
      domain, Unicode NFC local part).

    Parameters
    ----------
    email:
        The raw email address string to validate.

    Returns
    -------
    CheckResult
        PASS with normalized form in metadata, or FAIL with reason.

    Examples
    --------
    >>> result = check_syntax("John.Smith@Example.COM")
    >>> result.passed
    True
    >>> result.metadata["normalized"]
    'john.smith@example.com'

    >>> check_syntax("not-an-email").passed
    False
    """
    if not email or not isinstance(email, str):
        return CheckResult.fail(
            "Email must be a non-empty string",
            score_delta=-100,
        )

    email = email.strip()

    try:
        validated = validate_email(email, check_deliverability=False)
        # RFC 5321 says local parts are technically case-sensitive, but in
        # practice all real mail servers treat them case-insensitively.
        # We lowercase the full address for consistent storage and deduplication.
        normalized = validated.normalized.lower()
        logger.debug("syntax OK: %s → %s", email, normalized)
        return CheckResult.pass_(
            "Valid RFC 5322 syntax",
            normalized=normalized,
        )
    except EmailNotValidError as exc:
        logger.debug("syntax FAIL: %s — %s", email, exc)
        return CheckResult.fail(
            str(exc),
            score_delta=-100,
        )
