"""
ColdReach core Pydantic models.

These are the primary data structures that flow through the entire pipeline —
from source discovery through verification and into storage/output.

Design rules
------------
- Every model is immutable (frozen=False by default for update ergonomics,
  but validation runs on assignment).
- All email strings are normalized to lowercase on input.
- Confidence is always in range [0, 100].
- Timestamps are always UTC-naive datetimes (stored as UTC, no tz info
  embedded to keep SQLite simple).
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class VerificationStatus(StrEnum):
    """Result of the full verification pipeline for one email address."""

    VALID = "valid"
    """SMTP accepted the address and it's not a catch-all."""
    INVALID = "invalid"
    """Definitively invalid: bad syntax, NXDOMAIN, or SMTP 550."""
    RISKY = "risky"
    """Passes basic checks but has low-confidence signals."""
    UNKNOWN = "unknown"
    """Cannot determine — catch-all domain or SMTP unreachable."""
    CATCH_ALL = "catch_all"
    """Domain accepts all RCPT TO addresses — unverifiable via SMTP."""
    DISPOSABLE = "disposable"
    """Known throwaway / temporary email service."""
    UNDELIVERABLE = "undeliverable"
    """No MX records — domain cannot receive email."""


class EmailSource(StrEnum):
    """Where an email address was discovered."""

    WEBSITE_CONTACT = "website/contact"
    WEBSITE_TEAM = "website/team"
    WEBSITE_ABOUT = "website/about"
    WEBSITE_GENERIC = "website/other"
    THE_HARVESTER = "osint/theharvester"
    SPIDERFOOT = "osint/spiderfoot"
    GITHUB_COMMIT = "github/commit"
    GITHUB_PROFILE = "github/profile"
    WHOIS = "whois"
    REDDIT = "reddit"
    SEARXNG = "search/searxng"
    COMMON_CRAWL = "index/commoncrawl"
    PATTERN_GENERATED = "generated/pattern"
    HOLEHE = "verify/holehe"
    MANUAL = "manual"


# ---------------------------------------------------------------------------
# Supporting models
# ---------------------------------------------------------------------------


def _utcnow() -> datetime:
    """Return current UTC time as a timezone-naive datetime."""
    return datetime.now(UTC).replace(tzinfo=None)


class SourceRecord(BaseModel):
    """A single discovery event — one source that found one email."""

    source: EmailSource
    url: str | None = None
    """The page URL or API endpoint where the email was found."""
    context: str = ""
    """Surrounding text snippet or metadata that led to the discovery."""
    found_at: datetime = Field(default_factory=_utcnow)

    model_config = {"frozen": True}


# ---------------------------------------------------------------------------
# Primary result models
# ---------------------------------------------------------------------------


class EmailRecord(BaseModel):
    """A single email address with its verification state and discovery sources.

    Parameters
    ----------
    email:
        The email address (normalized to lowercase on input).
    confidence:
        Integer in [0, 100]. Higher = more likely to be valid and deliverable.
    status:
        Verification status from the pipeline.
    sources:
        All sources that discovered this address (de-duplicated upstream).
    is_catch_all_domain:
        True if the email's domain accepts all RCPT TO probes — SMTP
        verification is meaningless in this case.
    mx_records:
        MX hostnames for the domain, sorted by priority.
    holehe_platforms:
        Platform names where this email was confirmed registered (via Holehe).
    checked_at:
        When verification was last run.
    """

    email: str
    confidence: int = Field(ge=0, le=100)
    status: VerificationStatus = VerificationStatus.UNKNOWN
    sources: list[SourceRecord] = Field(default_factory=list)
    is_catch_all_domain: bool = False
    mx_records: list[str] = Field(default_factory=list)
    holehe_platforms: list[str] = Field(default_factory=list)
    checked_at: datetime = Field(default_factory=_utcnow)

    @field_validator("email")
    @classmethod
    def normalise_email(cls, v: str) -> str:
        """Lowercase and strip whitespace."""
        v = v.strip().lower()
        if "@" not in v or v.startswith("@") or v.endswith("@"):
            raise ValueError(f"Invalid email format: {v!r}")
        return v

    @property
    def domain(self) -> str:
        """The domain part of the email address."""
        return self.email.split("@")[1]

    @property
    def local_part(self) -> str:
        """The local (username) part of the email address."""
        return self.email.split("@")[0]

    @property
    def source_names(self) -> list[str]:
        """Deduplicated list of source identifiers that found this email."""
        seen: set[str] = set()
        result = []
        for s in self.sources:
            v = s.source.value
            if v not in seen:
                seen.add(v)
                result.append(v)
        return result

    @property
    def primary_source(self) -> str:
        """The highest-priority source that found this email."""
        return self.sources[0].source.value if self.sources else "unknown"

    def confidence_label(self) -> str:
        """Human-readable confidence tier."""
        if self.confidence >= 80:
            return "high"
        if self.confidence >= 50:
            return "medium"
        return "low"

    def to_dict(self) -> dict[str, Any]:
        """Flat dict suitable for CSV export."""
        return {
            "email": self.email,
            "confidence": self.confidence,
            "status": self.status.value,
            "sources": ", ".join(self.source_names),
            "is_catch_all": self.is_catch_all_domain,
            "holehe_platforms": ", ".join(self.holehe_platforms),
            "checked_at": self.checked_at.isoformat(),
        }


class DomainResult(BaseModel):
    """All email addresses discovered for one domain.

    Parameters
    ----------
    domain:
        The domain that was scanned (e.g. ``"stripe.com"``).
    company_name:
        Human-readable company name if known.
    emails:
        Discovered and verified email addresses.
    is_catch_all:
        True if the domain's mail server accepts all RCPT TO probes.
    mx_records:
        MX records for the domain.
    crawled_at:
        Timestamp when the scan completed.
    """

    domain: str
    company_name: str | None = None
    emails: list[EmailRecord] = Field(default_factory=list)
    is_catch_all: bool = False
    mx_records: list[str] = Field(default_factory=list)
    crawled_at: datetime = Field(default_factory=_utcnow)

    @field_validator("domain")
    @classmethod
    def normalise_domain(cls, v: str) -> str:
        return v.strip().lower().removeprefix("www.")

    @property
    def best_email(self) -> EmailRecord | None:
        """Return the email with the highest confidence score."""
        if not self.emails:
            return None
        return max(self.emails, key=lambda e: e.confidence)

    def sorted_emails(self, min_confidence: int = 0) -> list[EmailRecord]:
        """Return emails sorted by confidence descending.

        Parameters
        ----------
        min_confidence:
            Exclude emails below this confidence threshold.
        """
        filtered = [e for e in self.emails if e.confidence >= min_confidence]
        return sorted(filtered, key=lambda e: e.confidence, reverse=True)

    def add_email(self, record: EmailRecord) -> None:
        """Add or merge an email record, avoiding exact duplicates."""
        for existing in self.emails:
            if existing.email == record.email:
                return  # already tracked
        self.emails.append(record)

    def __len__(self) -> int:
        return len(self.emails)

    def __repr__(self) -> str:
        return f"DomainResult(domain={self.domain!r}, emails={len(self.emails)})"
