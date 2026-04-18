"""
Domain email format learner.

Infers a company's email format from confirmed addresses at that domain,
then generates targeted candidates for a specific person — only the format(s)
that match the domain's known pattern.

This avoids the shotgun approach of generating all 12 variants and running each
through SMTP verification (expensive and likely to trigger rate limits).

Confidence tiers:
  - Known format match  → confidence_hint = 10  (format confirmed from real emails)
  - Blind guess         → confidence_hint =  5  (no known emails, guessing top-3 formats)

Example
-------
    from coldreach.generate.learner import targeted_patterns

    # Domain uses "first.last" format (inferred from jane.doe@acme.com)
    patterns = targeted_patterns("John Smith", "acme.com", ["jane.doe@acme.com"])
    # → [EmailPattern("john.smith@acme.com", "first.last")]

    # Domain format unknown — return top-3 guesses
    patterns = targeted_patterns("John Smith", "acme.com", [])
    # → [EmailPattern("john.smith@acme.com", "first.last"),
    #    EmailPattern("jsmith@acme.com", "flast"),
    #    EmailPattern("john@acme.com", "first")]
"""

from __future__ import annotations

import logging

from coldreach.generate.patterns import EmailPattern, generate_patterns, most_likely_format

logger = logging.getLogger(__name__)

# Fallback formats when domain pattern is unknown — ordered by B2B prevalence.
# Based on analysis of 100k+ corporate email addresses.
_FALLBACK_FORMATS = ["first.last", "flast", "first"]

# Formats that are so similar they should both be emitted when one matches.
# E.g. if we see "first.last", also include "flast" since both are very common.
_COMPANION_FORMATS: dict[str, list[str]] = {
    "first.last": ["flast"],
    "flast":      ["first.last"],
    "f.last":     ["first.last"],
    "first":      ["first.last"],
}


def learn_format(known_emails: list[str], domain: str) -> str | None:
    """Return the most likely email format_name for *domain*.

    Analyses the local parts of *known_emails* and returns the format_name
    (e.g. ``"first.last"``, ``"flast"``) that best describes them.

    Returns ``None`` if the format cannot be determined (too few emails,
    or local parts are too ambiguous like role addresses ``info@``, ``hr@``).
    """
    fmt = most_likely_format(known_emails, domain)
    if fmt:
        logger.debug("Format learner: %s → %s (from %d email(s))", domain, fmt, len(known_emails))
    else:
        logger.debug("Format learner: %s → unknown (from %d email(s))", domain, len(known_emails))
    return fmt


def targeted_patterns(
    full_name: str,
    domain: str,
    known_emails: list[str],
    *,
    max_fallback: int = 3,
) -> list[EmailPattern]:
    """Generate targeted email candidates for *full_name* at *domain*.

    When a domain format can be inferred from *known_emails*, only patterns
    matching that format (plus close companions) are returned.

    When the format is unknown, the *max_fallback* most common B2B formats
    are returned.

    Parameters
    ----------
    full_name:
        Person's full name, e.g. ``"John Smith"``.
    domain:
        Company domain, e.g. ``"acme.com"``.
    known_emails:
        Confirmed email addresses at *domain* (used to infer format).
    max_fallback:
        Number of fallback formats to try when domain format is unknown.

    Returns
    -------
    list[EmailPattern]
        Targeted candidates, deduplicated, ordered by confidence.
        Empty if *full_name* cannot be parsed.
    """
    all_patterns = generate_patterns(full_name, domain)
    if not all_patterns:
        return []

    # Index patterns by format_name for quick lookup
    by_format: dict[str, EmailPattern] = {p.format_name: p for p in all_patterns}

    inferred = learn_format(known_emails, domain) if known_emails else None

    if inferred and inferred in by_format:
        # Pick the inferred format + any companions
        selected_formats = [inferred] + [
            f for f in _COMPANION_FORMATS.get(inferred, []) if f in by_format
        ]
    else:
        # No known format — use fallback list
        selected_formats = [f for f in _FALLBACK_FORMATS if f in by_format][:max_fallback]

    # Build final list, preserving order, deduplicating by email address
    seen_emails: set[str] = set()
    result: list[EmailPattern] = []
    for fmt in selected_formats:
        pat = by_format.get(fmt)
        if pat and pat.email not in seen_emails:
            seen_emails.add(pat.email)
            result.append(pat)

    logger.debug(
        "Learner generated %d candidate(s) for '%s' at %s (inferred: %s)",
        len(result),
        full_name,
        domain,
        inferred or "unknown",
    )
    return result
