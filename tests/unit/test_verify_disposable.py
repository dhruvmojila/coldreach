"""
Unit tests for coldreach.verify.disposable

All tests are pure CPU — the blocklist is loaded from the bundled .txt file.
No network calls, no external services.
"""

from __future__ import annotations

import pytest

from coldreach.verify.disposable import (
    _load_domains,
    check_disposable,
    is_disposable,
)


class TestLoadDomains:
    """Tests that the bundled blocklist loads correctly."""

    def test_blocklist_is_not_empty(self) -> None:
        domains = _load_domains()
        assert len(domains) > 100, "Blocklist should contain at least 100 domains"

    def test_blocklist_contains_mailinator(self) -> None:
        assert "mailinator.com" in _load_domains()

    def test_blocklist_contains_yopmail(self) -> None:
        assert "yopmail.com" in _load_domains()

    def test_blocklist_contains_guerrillamail(self) -> None:
        assert "guerrillamail.com" in _load_domains()

    def test_blocklist_contains_10minutemail(self) -> None:
        assert "10minutemail.com" in _load_domains()

    def test_blocklist_contains_trashmail(self) -> None:
        assert "trashmail.com" in _load_domains()

    def test_blocklist_contains_tempmail(self) -> None:
        assert "tempmail.com" in _load_domains()

    def test_all_domains_are_lowercase(self) -> None:
        for domain in _load_domains():
            assert domain == domain.lower(), f"Domain not lowercase: {domain!r}"

    def test_no_empty_strings(self) -> None:
        for domain in _load_domains():
            assert domain.strip() != "", "Found empty string in blocklist"

    def test_no_comment_lines_included(self) -> None:
        for domain in _load_domains():
            assert not domain.startswith("#"), f"Comment leaked into blocklist: {domain!r}"


class TestIsDisposable:
    """Tests for the is_disposable() boolean helper."""

    def test_mailinator_is_disposable(self) -> None:
        assert is_disposable("test@mailinator.com") is True

    def test_yopmail_is_disposable(self) -> None:
        assert is_disposable("abc@yopmail.com") is True

    def test_guerrillamail_is_disposable(self) -> None:
        assert is_disposable("x@guerrillamail.com") is True

    def test_gmail_is_not_disposable(self) -> None:
        assert is_disposable("user@gmail.com") is False

    def test_outlook_is_not_disposable(self) -> None:
        assert is_disposable("user@outlook.com") is False

    def test_corporate_domain_is_not_disposable(self) -> None:
        assert is_disposable("john@stripe.com") is False

    def test_case_insensitive_domain_check(self) -> None:
        assert is_disposable("test@MAILINATOR.COM") is True
        assert is_disposable("test@Mailinator.Com") is True

    def test_invalid_email_without_at_returns_false(self) -> None:
        # is_disposable should not raise on bad input
        assert is_disposable("notanemail") is False

    def test_empty_string_returns_false(self) -> None:
        assert is_disposable("") is False


class TestCheckDisposable:
    """Tests for the pipeline-compatible check_disposable() function."""

    def test_disposable_email_fails(self) -> None:
        result = check_disposable("user@mailinator.com")
        assert result.failed

    def test_disposable_has_negative_score_delta(self) -> None:
        result = check_disposable("user@mailinator.com")
        assert result.score_delta < 0

    def test_disposable_reason_mentions_domain(self) -> None:
        result = check_disposable("user@mailinator.com")
        assert "mailinator.com" in result.reason

    def test_disposable_metadata_has_domain(self) -> None:
        result = check_disposable("user@mailinator.com")
        assert result.metadata.get("domain") == "mailinator.com"

    def test_legitimate_email_passes(self) -> None:
        result = check_disposable("john@stripe.com")
        assert result.passed

    def test_legitimate_email_has_positive_score(self) -> None:
        result = check_disposable("john@stripe.com")
        assert result.score_delta > 0

    def test_legitimate_email_metadata_has_domain(self) -> None:
        result = check_disposable("john@stripe.com")
        assert result.metadata.get("domain") == "stripe.com"

    def test_yopmail_fails(self) -> None:
        result = check_disposable("hello@yopmail.com")
        assert result.failed

    def test_sharklasers_fails(self) -> None:
        result = check_disposable("x@sharklasers.com")
        assert result.failed

    def test_trashmail_fails(self) -> None:
        result = check_disposable("trash@trashmail.com")
        assert result.failed

    def test_empty_email_returns_skip(self) -> None:
        result = check_disposable("")
        assert result.skipped

    def test_email_without_at_returns_skip(self) -> None:
        result = check_disposable("notanemail")
        assert result.skipped
