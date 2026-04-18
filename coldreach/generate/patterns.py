"""
Email pattern generator — produces candidate addresses from a person's name + domain.

Given a full name like "John Smith" and domain "acme.com", generates the 12
most common professional email formats used by B2B companies:

  john@acme.com
  john.smith@acme.com
  jsmith@acme.com
  j.smith@acme.com
  smithj@acme.com
  smith.j@acme.com
  johnsmith@acme.com
  smith@acme.com
  johns@acme.com
  john-smith@acme.com
  j-smith@acme.com
  js@acme.com

Names are normalised: accents stripped, hyphenated names split, suffixes
(Jr, Sr, III, etc.) removed before pattern expansion.

Usage
-----
    from coldreach.generate.patterns import generate_patterns

    candidates = generate_patterns("John Smith", "acme.com")
    # → [EmailPattern(email="john@acme.com", format_name="first"), ...]
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Name normalisation
# ---------------------------------------------------------------------------

_SUFFIXES = frozenset(["jr", "sr", "ii", "iii", "iv", "v", "phd", "md", "esq", "dds", "cpa"])


def _strip_accents(text: str) -> str:
    """Decompose unicode → strip combining characters → ASCII."""
    nfd = unicodedata.normalize("NFD", text)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def _clean_name_part(part: str) -> str:
    """Lowercase, strip accents, remove non-alpha characters."""
    part = _strip_accents(part).lower()
    return re.sub(r"[^a-z]", "", part)


def _parse_name(full_name: str) -> tuple[str, str]:
    """Return (first, last) from a full name string.

    Handles:
    - "John Smith"           → ("john", "smith")
    - "John Paul Smith"      → ("john", "smith")   middle name dropped
    - "Mary-Jane Watson"     → ("maryjane", "watson")
    - "José García Jr."      → ("jose", "garcia")  accent + suffix stripped
    - "Smith"                → ("smith", "")        single token
    """
    parts = full_name.strip().split()
    cleaned: list[str] = []
    for p in parts:
        # Split hyphenated names: "Mary-Jane" → ["Mary", "Jane"]
        subparts = p.replace("-", " ").split()
        for sp in subparts:
            c = _clean_name_part(sp)
            if c and c not in _SUFFIXES:
                cleaned.append(c)

    if not cleaned:
        return ("", "")
    if len(cleaned) == 1:
        return (cleaned[0], "")

    first = cleaned[0]
    last = cleaned[-1]  # use last token as surname (ignores middle names)
    return (first, last)


# ---------------------------------------------------------------------------
# Pattern dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EmailPattern:
    """A single generated email candidate.

    Attributes
    ----------
    email:
        The generated email address (already lowercased).
    format_name:
        Short identifier for the pattern (e.g. ``"first.last"``).
    """

    email: str
    format_name: str


# ---------------------------------------------------------------------------
# Pattern generation
# ---------------------------------------------------------------------------


def generate_patterns(full_name: str, domain: str) -> list[EmailPattern]:
    """Generate candidate email addresses for *full_name* at *domain*.

    Parameters
    ----------
    full_name:
        The person's full name, e.g. ``"John Smith"``.
    domain:
        The company domain, e.g. ``"acme.com"``.

    Returns
    -------
    list[EmailPattern]
        Deduplicated list of candidates ordered from most-common to least.
        Empty list if name cannot be parsed (e.g. empty string).

    Examples
    --------
    >>> patterns = generate_patterns("John Smith", "acme.com")
    >>> [p.format_name for p in patterns[:3]]
    ['first', 'first.last', 'flast']
    """
    domain = domain.strip().lower().removeprefix("www.")
    first, last = _parse_name(full_name)

    if not first:
        return []

    f = first
    l = last  # noqa: E741
    fi = f[0] if f else ""
    li = l[0] if l else ""

    # Build candidates in priority order (most common B2B formats first)
    raw: list[tuple[str, str]] = []

    if l:
        raw = [
            (f"{f}", "first"),
            (f"{f}.{l}", "first.last"),
            (f"{fi}{l}", "flast"),
            (f"{fi}.{l}", "f.last"),
            (f"{l}{fi}", "lastf"),
            (f"{l}.{fi}", "last.f"),
            (f"{f}{l}", "firstlast"),
            (f"{l}", "last"),
            (f"{f}{li}", "firsts"),  # e.g. johns (first + last initial)
            (f"{f}-{l}", "first-last"),
            (f"{fi}-{l}", "f-last"),
            (f"{fi}{li}", "initials"),
        ]
    else:
        # Single-token name — only generate what makes sense
        raw = [
            (f"{f}", "first"),
        ]

    # Deduplicate while preserving order
    seen: set[str] = set()
    results: list[EmailPattern] = []
    for local, fmt in raw:
        if not local or local in seen:
            continue
        seen.add(local)
        results.append(EmailPattern(email=f"{local}@{domain}", format_name=fmt))

    return results


# Role-based addresses common in B2B outreach — ordered by usefulness
_ROLE_LOCALS = [
    "info",
    "contact",
    "hello",
    "sales",
    "marketing",
    "partnerships",
    "press",
    "support",
    "business",
    "growth",
]


def generate_role_emails(domain: str) -> list[EmailPattern]:
    """Generate common role-based email candidates for *domain*.

    Returns candidates like ``info@domain.com``, ``sales@domain.com``.
    These are low-confidence guesses — always verify before using.

    Parameters
    ----------
    domain:
        The company domain, e.g. ``"acme.com"``.

    Returns
    -------
    list[EmailPattern]
        Role email candidates with ``format_name`` like ``"role:info"``.
    """
    domain = domain.strip().lower().removeprefix("www.")
    return [
        EmailPattern(email=f"{role}@{domain}", format_name=f"role:{role}")
        for role in _ROLE_LOCALS
    ]


def most_likely_format(known_emails: list[str], domain: str) -> str | None:
    """Infer the most common email format from a list of known addresses.

    Useful when you already have one confirmed email at a domain and want
    to generate candidates for other people using the same format.

    Parameters
    ----------
    known_emails:
        List of confirmed email addresses at the domain.
    domain:
        The domain to analyse.

    Returns
    -------
    str | None
        The ``format_name`` of the most common pattern, or ``None`` if
        it cannot be determined.

    Examples
    --------
    >>> most_likely_format(["john.smith@acme.com", "jane.doe@acme.com"], "acme.com")
    'first.last'
    """
    from collections import Counter

    format_counts: Counter[str] = Counter()

    for email in known_emails:
        if "@" not in email:
            continue
        local, email_domain = email.lower().rsplit("@", 1)
        if email_domain != domain:
            continue

        # Classify the local part into a pattern
        if "." in local:
            parts = local.split(".", 1)
            if len(parts[0]) == 1:
                format_counts["f.last"] += 1
            elif len(parts[1]) == 1:
                format_counts["last.f"] += 1
            else:
                format_counts["first.last"] += 1
        elif "-" in local:
            parts = local.split("-", 1)
            if len(parts[0]) == 1:
                format_counts["f-last"] += 1
            else:
                format_counts["first-last"] += 1
        elif len(local) <= 3:
            format_counts["initials"] += 1
        elif len(local) <= 6:
            format_counts["flast"] += 1
        else:
            format_counts["firstlast"] += 1

    if not format_counts:
        return None
    return format_counts.most_common(1)[0][0]
