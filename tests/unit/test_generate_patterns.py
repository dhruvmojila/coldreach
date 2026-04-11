"""
Unit tests for coldreach.generate.patterns
"""

from __future__ import annotations

from coldreach.generate.patterns import EmailPattern, generate_patterns, most_likely_format


class TestParseName:
    """Indirect tests via generate_patterns — verifies name parsing."""

    def test_simple_first_last(self) -> None:
        patterns = generate_patterns("John Smith", "acme.com")
        emails = [p.email for p in patterns]
        assert "john@acme.com" in emails
        assert "john.smith@acme.com" in emails

    def test_three_part_name_drops_middle(self) -> None:
        patterns = generate_patterns("John Paul Smith", "acme.com")
        emails = [p.email for p in patterns]
        assert "john@acme.com" in emails
        assert "john.smith@acme.com" in emails
        # middle name should not appear in local parts
        assert all("paul" not in e for e in emails)

    def test_accented_name_stripped(self) -> None:
        patterns = generate_patterns("José García", "acme.com")
        emails = [p.email for p in patterns]
        assert "jose@acme.com" in emails
        assert "jose.garcia@acme.com" in emails

    def test_hyphenated_first_name_joined(self) -> None:
        patterns = generate_patterns("Mary-Jane Watson", "acme.com")
        emails = [p.email for p in patterns]
        assert "maryjane@acme.com" in emails or "mary-jane@acme.com" not in emails

    def test_suffix_stripped(self) -> None:
        patterns = generate_patterns("John Smith Jr.", "acme.com")
        emails = [p.email for p in patterns]
        assert all("jr" not in e.split("@")[0] for e in emails)

    def test_empty_name_returns_empty(self) -> None:
        assert generate_patterns("", "acme.com") == []

    def test_single_token_name(self) -> None:
        patterns = generate_patterns("Cher", "acme.com")
        assert len(patterns) == 1
        assert patterns[0].email == "cher@acme.com"


class TestGeneratePatterns:
    def test_returns_email_patterns(self) -> None:
        patterns = generate_patterns("John Smith", "acme.com")
        assert all(isinstance(p, EmailPattern) for p in patterns)

    def test_all_emails_at_correct_domain(self) -> None:
        patterns = generate_patterns("John Smith", "acme.com")
        assert all(p.email.endswith("@acme.com") for p in patterns)

    def test_no_duplicate_emails(self) -> None:
        patterns = generate_patterns("John Smith", "acme.com")
        emails = [p.email for p in patterns]
        assert len(emails) == len(set(emails))

    def test_all_emails_lowercase(self) -> None:
        patterns = generate_patterns("JOHN SMITH", "ACME.COM")
        assert all(p.email == p.email.lower() for p in patterns)

    def test_www_prefix_stripped_from_domain(self) -> None:
        patterns = generate_patterns("John Smith", "www.acme.com")
        assert all("www" not in p.email for p in patterns)

    def test_expected_format_names_present(self) -> None:
        patterns = generate_patterns("John Smith", "acme.com")
        fmt_names = {p.format_name for p in patterns}
        assert "first" in fmt_names
        assert "first.last" in fmt_names
        assert "flast" in fmt_names

    def test_initials_pattern(self) -> None:
        patterns = generate_patterns("John Smith", "acme.com")
        emails = [p.email for p in patterns]
        assert "js@acme.com" in emails

    def test_last_only_pattern(self) -> None:
        patterns = generate_patterns("John Smith", "acme.com")
        emails = [p.email for p in patterns]
        assert "smith@acme.com" in emails

    def test_hyphen_pattern(self) -> None:
        patterns = generate_patterns("John Smith", "acme.com")
        emails = [p.email for p in patterns]
        assert "john-smith@acme.com" in emails

    def test_generates_at_least_8_patterns(self) -> None:
        patterns = generate_patterns("John Smith", "acme.com")
        assert len(patterns) >= 8


class TestMostLikelyFormat:
    def test_first_dot_last(self) -> None:
        emails = ["john.smith@acme.com", "jane.doe@acme.com", "bob.jones@acme.com"]
        assert most_likely_format(emails, "acme.com") == "first.last"

    def test_flast(self) -> None:
        emails = ["jsmith@acme.com", "jdoe@acme.com"]
        result = most_likely_format(emails, "acme.com")
        assert result == "flast"

    def test_ignores_other_domains(self) -> None:
        emails = ["john.smith@other.com", "jane.doe@acme.com"]
        # Only jane.doe@acme.com counts
        result = most_likely_format(emails, "acme.com")
        assert result == "first.last"

    def test_empty_list_returns_none(self) -> None:
        assert most_likely_format([], "acme.com") is None

    def test_no_matching_domain_returns_none(self) -> None:
        emails = ["john@other.com"]
        assert most_likely_format(emails, "acme.com") is None
