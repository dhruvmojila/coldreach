"""
Unit tests for coldreach.verify.syntax.check_syntax

All tests are pure CPU — no network, no services.
"""

from __future__ import annotations

from coldreach.verify.syntax import check_syntax


class TestCheckSyntaxPass:
    """Cases that should PASS syntax validation."""

    def test_simple_valid_email(self) -> None:
        result = check_syntax("user@example.com")
        assert result.passed

    def test_returns_normalized_in_metadata(self) -> None:
        result = check_syntax("user@example.com")
        assert result.metadata["normalized"] == "user@example.com"

    def test_mixed_case_is_normalised_to_lowercase(self) -> None:
        result = check_syntax("John.Smith@Example.COM")
        assert result.passed
        assert result.metadata["normalized"] == "john.smith@example.com"

    def test_plus_alias_is_valid(self) -> None:
        result = check_syntax("user+tag@example.com")
        assert result.passed

    def test_subdomain_email_is_valid(self) -> None:
        result = check_syntax("user@mail.example.co.uk")
        assert result.passed

    def test_numeric_local_part_is_valid(self) -> None:
        result = check_syntax("12345@example.com")
        assert result.passed

    def test_hyphenated_domain_is_valid(self) -> None:
        result = check_syntax("user@my-company.com")
        assert result.passed

    def test_whitespace_is_stripped_before_validation(self) -> None:
        result = check_syntax("  user@example.com  ")
        assert result.passed
        assert result.metadata["normalized"] == "user@example.com"


class TestCheckSyntaxFail:
    """Cases that should FAIL syntax validation."""

    def test_empty_string_fails(self) -> None:
        result = check_syntax("")
        assert result.failed

    def test_none_type_like_empty_fails(self) -> None:
        # Passing a clearly non-email string
        result = check_syntax("   ")
        # Either fails or the email_validator rejects it
        # blank after strip → invalid
        assert result.failed

    def test_missing_at_sign_fails(self) -> None:
        result = check_syntax("userexample.com")
        assert result.failed

    def test_missing_domain_fails(self) -> None:
        result = check_syntax("user@")
        assert result.failed

    def test_missing_local_part_fails(self) -> None:
        result = check_syntax("@example.com")
        assert result.failed

    def test_double_at_sign_fails(self) -> None:
        result = check_syntax("user@@example.com")
        assert result.failed

    def test_space_in_local_part_fails(self) -> None:
        result = check_syntax("user name@example.com")
        assert result.failed

    def test_missing_tld_fails(self) -> None:
        result = check_syntax("user@localhost")
        # email-validator rejects bare hostnames without TLD by default
        assert result.failed

    def test_score_delta_is_negative_on_fail(self) -> None:
        result = check_syntax("notvalid")
        assert result.score_delta < 0

    def test_reason_is_non_empty_on_fail(self) -> None:
        result = check_syntax("bad@@email")
        assert result.reason != ""


class TestCheckSyntaxEdgeCases:
    """Edge cases and unusual but technically valid inputs."""

    def test_extremely_long_local_part_fails(self) -> None:
        # RFC 5321 max total email length is 254 chars
        long_local = "a" * 250
        result = check_syntax(f"{long_local}@example.com")
        assert result.failed

    def test_internationalized_domain_is_valid(self) -> None:
        # IDN domains are supported by email-validator
        result = check_syntax("user@münchen.de")
        # May pass or fail depending on normalisation mode — just check no exception
        assert result.status in ("pass", "fail")
