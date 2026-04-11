"""
Unit tests for coldreach.core.models

Pure data model tests — no I/O.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from coldreach.core.models import (
    DomainResult,
    EmailRecord,
    EmailSource,
    SourceRecord,
    VerificationStatus,
)


class TestEmailRecord:
    """Tests for the EmailRecord Pydantic model."""

    def test_valid_email_accepted(self) -> None:
        record = EmailRecord(email="john@example.com", confidence=75)
        assert record.email == "john@example.com"

    def test_email_normalised_to_lowercase(self) -> None:
        record = EmailRecord(email="John@Example.COM", confidence=50)
        assert record.email == "john@example.com"

    def test_email_whitespace_stripped(self) -> None:
        record = EmailRecord(email="  user@example.com  ", confidence=40)
        assert record.email == "user@example.com"

    def test_confidence_zero_accepted(self) -> None:
        record = EmailRecord(email="user@example.com", confidence=0)
        assert record.confidence == 0

    def test_confidence_100_accepted(self) -> None:
        record = EmailRecord(email="user@example.com", confidence=100)
        assert record.confidence == 100

    def test_confidence_above_100_raises(self) -> None:
        with pytest.raises(ValidationError):
            EmailRecord(email="user@example.com", confidence=101)

    def test_confidence_below_0_raises(self) -> None:
        with pytest.raises(ValidationError):
            EmailRecord(email="user@example.com", confidence=-1)

    def test_invalid_email_raises(self) -> None:
        with pytest.raises(ValidationError):
            EmailRecord(email="notanemail", confidence=50)

    def test_email_missing_at_raises(self) -> None:
        with pytest.raises(ValidationError):
            EmailRecord(email="example.com", confidence=50)

    def test_default_status_is_unknown(self) -> None:
        record = EmailRecord(email="user@example.com", confidence=50)
        assert record.status == VerificationStatus.UNKNOWN

    def test_domain_property(self) -> None:
        record = EmailRecord(email="user@stripe.com", confidence=70)
        assert record.domain == "stripe.com"

    def test_local_part_property(self) -> None:
        record = EmailRecord(email="patrick@stripe.com", confidence=70)
        assert record.local_part == "patrick"

    def test_source_names_empty_by_default(self) -> None:
        record = EmailRecord(email="user@example.com", confidence=50)
        assert record.source_names == []

    def test_source_names_deduplicates(self) -> None:
        record = EmailRecord(
            email="user@example.com",
            confidence=50,
            sources=[
                SourceRecord(source=EmailSource.WEBSITE_CONTACT),
                SourceRecord(source=EmailSource.WEBSITE_CONTACT),  # duplicate
                SourceRecord(source=EmailSource.GITHUB_COMMIT),
            ],
        )
        names = record.source_names
        assert names.count("website/contact") == 1
        assert "github/commit" in names

    def test_primary_source_returns_first_source(self) -> None:
        record = EmailRecord(
            email="user@example.com",
            confidence=50,
            sources=[
                SourceRecord(source=EmailSource.WEBSITE_TEAM),
                SourceRecord(source=EmailSource.GITHUB_COMMIT),
            ],
        )
        assert record.primary_source == "website/team"

    def test_primary_source_unknown_when_no_sources(self) -> None:
        record = EmailRecord(email="user@example.com", confidence=50)
        assert record.primary_source == "unknown"

    def test_confidence_label_high(self) -> None:
        record = EmailRecord(email="user@example.com", confidence=80)
        assert record.confidence_label() == "high"

    def test_confidence_label_medium(self) -> None:
        record = EmailRecord(email="user@example.com", confidence=65)
        assert record.confidence_label() == "medium"

    def test_confidence_label_low(self) -> None:
        record = EmailRecord(email="user@example.com", confidence=30)
        assert record.confidence_label() == "low"

    def test_to_dict_has_required_keys(self) -> None:
        record = EmailRecord(email="user@example.com", confidence=60)
        d = record.to_dict()
        assert "email" in d
        assert "confidence" in d
        assert "status" in d
        assert "sources" in d


class TestDomainResult:
    """Tests for the DomainResult Pydantic model."""

    def test_empty_domain_result(self) -> None:
        result = DomainResult(domain="example.com")
        assert result.domain == "example.com"
        assert result.emails == []

    def test_domain_normalised_to_lowercase(self) -> None:
        result = DomainResult(domain="Example.COM")
        assert result.domain == "example.com"

    def test_www_prefix_stripped(self) -> None:
        result = DomainResult(domain="www.example.com")
        assert result.domain == "example.com"

    def test_best_email_is_none_when_empty(self) -> None:
        result = DomainResult(domain="example.com")
        assert result.best_email is None

    def test_best_email_returns_highest_confidence(self) -> None:
        result = DomainResult(
            domain="example.com",
            emails=[
                EmailRecord(email="a@example.com", confidence=30),
                EmailRecord(email="b@example.com", confidence=90),
                EmailRecord(email="c@example.com", confidence=60),
            ],
        )
        assert result.best_email is not None
        assert result.best_email.email == "b@example.com"

    def test_sorted_emails_descending_by_confidence(self) -> None:
        result = DomainResult(
            domain="example.com",
            emails=[
                EmailRecord(email="a@example.com", confidence=30),
                EmailRecord(email="b@example.com", confidence=80),
                EmailRecord(email="c@example.com", confidence=55),
            ],
        )
        sorted_list = result.sorted_emails()
        assert sorted_list[0].email == "b@example.com"
        assert sorted_list[-1].email == "a@example.com"

    def test_sorted_emails_respects_min_confidence(self) -> None:
        result = DomainResult(
            domain="example.com",
            emails=[
                EmailRecord(email="a@example.com", confidence=30),
                EmailRecord(email="b@example.com", confidence=80),
            ],
        )
        filtered = result.sorted_emails(min_confidence=50)
        assert len(filtered) == 1
        assert filtered[0].email == "b@example.com"

    def test_add_email_appends_new_address(self) -> None:
        result = DomainResult(domain="example.com")
        record = EmailRecord(email="new@example.com", confidence=50)
        result.add_email(record)
        assert len(result.emails) == 1

    def test_add_email_deduplicates_by_address(self) -> None:
        result = DomainResult(domain="example.com")
        record = EmailRecord(email="user@example.com", confidence=50)
        result.add_email(record)
        result.add_email(record)  # same email again
        assert len(result.emails) == 1

    def test_len_returns_email_count(self) -> None:
        result = DomainResult(
            domain="example.com",
            emails=[
                EmailRecord(email="a@example.com", confidence=40),
                EmailRecord(email="b@example.com", confidence=60),
            ],
        )
        assert len(result) == 2
