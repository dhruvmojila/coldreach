"""
Unit tests for coldreach.generate.learner

All tests are pure (no network, no I/O).
"""

from __future__ import annotations

from coldreach.generate.learner import learn_format, targeted_patterns
from coldreach.generate.patterns import EmailPattern


class TestLearnFormat:
    def test_detects_first_dot_last(self) -> None:
        emails = ["jane.doe@acme.com", "bob.jones@acme.com"]
        assert learn_format(emails, "acme.com") == "first.last"

    def test_detects_flast(self) -> None:
        emails = ["jdoe@acme.com", "bsmith@acme.com"]
        assert learn_format(emails, "acme.com") == "flast"

    def test_detects_f_dot_last(self) -> None:
        emails = ["j.doe@acme.com", "b.smith@acme.com"]
        assert learn_format(emails, "acme.com") == "f.last"

    def test_returns_none_for_empty_list(self) -> None:
        assert learn_format([], "acme.com") is None

    def test_ignores_emails_from_other_domains(self) -> None:
        result = learn_format(["john.doe@other.com"], "acme.com")
        assert result is None

    def test_most_common_wins(self) -> None:
        # 2x first.last vs 1x flast -> first.last wins
        emails = [
            "john.smith@acme.com",
            "jane.doe@acme.com",
            "bwilson@acme.com",
        ]
        assert learn_format(emails, "acme.com") == "first.last"


class TestTargetedPatterns:
    def test_returns_matching_format_when_known(self) -> None:
        # Domain uses first.last — should get john.smith
        patterns = targeted_patterns(
            "John Smith", "acme.com", ["jane.doe@acme.com", "bob.jones@acme.com"]
        )
        emails = [p.email for p in patterns]
        assert "john.smith@acme.com" in emails

    def test_known_format_excludes_unrelated_formats(self) -> None:
        # first.last domain — should NOT include initials (js@acme.com)
        patterns = targeted_patterns(
            "John Smith", "acme.com", ["jane.doe@acme.com"]
        )
        emails = [p.email for p in patterns]
        assert "js@acme.com" not in emails

    def test_companion_format_included(self) -> None:
        # first.last → companion is flast (jsmith@acme.com)
        patterns = targeted_patterns(
            "John Smith", "acme.com", ["jane.doe@acme.com"]
        )
        emails = [p.email for p in patterns]
        assert "john.smith@acme.com" in emails
        assert "jsmith@acme.com" in emails

    def test_fallback_formats_when_no_known_emails(self) -> None:
        patterns = targeted_patterns("John Smith", "acme.com", [])
        emails = [p.email for p in patterns]
        # Should include the top-3 fallback formats
        assert "john.smith@acme.com" in emails  # first.last
        assert "jsmith@acme.com" in emails       # flast
        assert "john@acme.com" in emails         # first

    def test_fallback_capped_at_max_fallback(self) -> None:
        patterns = targeted_patterns("John Smith", "acme.com", [], max_fallback=1)
        assert len(patterns) == 1

    def test_returns_empty_for_unparseable_name(self) -> None:
        assert targeted_patterns("", "acme.com", []) == []

    def test_no_duplicates_in_output(self) -> None:
        patterns = targeted_patterns("John Smith", "acme.com", ["jane.doe@acme.com"])
        emails = [p.email for p in patterns]
        assert len(emails) == len(set(emails))

    def test_returns_email_pattern_objects(self) -> None:
        patterns = targeted_patterns("Jane Doe", "acme.com", [])
        assert all(isinstance(p, EmailPattern) for p in patterns)

    def test_correct_domain_in_output(self) -> None:
        patterns = targeted_patterns("John Smith", "stripe.com", [])
        assert all(p.email.endswith("@stripe.com") for p in patterns)

    def test_handles_single_name(self) -> None:
        # Only first name — should still work
        patterns = targeted_patterns("John", "acme.com", [])
        assert len(patterns) >= 1
        assert patterns[0].email == "john@acme.com"

    def test_flast_domain_generates_flast_first(self) -> None:
        patterns = targeted_patterns(
            "John Smith", "acme.com", ["jdoe@acme.com", "bwilson@acme.com"]
        )
        # First result should be flast format
        assert patterns[0].format_name == "flast"
        assert patterns[0].email == "jsmith@acme.com"
