"""
Unit tests for coldreach.verify.pipeline.run_basic_pipeline

DNS is mocked — no real network calls.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import dns.resolver
import pytest

from coldreach.verify.pipeline import PipelineResult, run_basic_pipeline

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mx_answer(hostname: str, preference: int = 10) -> MagicMock:
    rdata = MagicMock()
    rdata.preference = preference
    rdata.exchange = MagicMock()
    rdata.exchange.__str__ = lambda self: f"{hostname}."
    return rdata


# ---------------------------------------------------------------------------
# PipelineResult unit tests
# ---------------------------------------------------------------------------


class TestPipelineResult:
    """Tests for the PipelineResult dataclass itself."""

    def test_score_clamped_to_100(self) -> None:
        from coldreach.verify._types import CheckResult

        result = PipelineResult(email="x@example.com", base_score=90)
        result.checks["a"] = CheckResult.pass_(score_delta=30)
        assert result.score == 100

    def test_score_clamped_to_0(self) -> None:
        from coldreach.verify._types import CheckResult

        result = PipelineResult(email="x@example.com", base_score=10)
        result.checks["a"] = CheckResult.fail("bad", score_delta=-100)
        assert result.score == 0

    def test_passed_false_when_any_check_fails(self) -> None:
        from coldreach.verify._types import CheckResult

        result = PipelineResult(email="x@example.com")
        result.checks["syntax"] = CheckResult.pass_()
        result.checks["dns"] = CheckResult.fail("no mx")
        assert result.passed is False

    def test_passed_true_when_all_checks_pass(self) -> None:
        from coldreach.verify._types import CheckResult

        result = PipelineResult(email="user@example.com")
        result.checks["syntax"] = CheckResult.pass_(normalized="user@example.com")
        result.checks["disposable"] = CheckResult.pass_()
        result.checks["dns"] = CheckResult.pass_(mx_records=["mail.example.com"])
        assert result.passed is True

    def test_normalized_email_from_syntax_metadata(self) -> None:
        from coldreach.verify._types import CheckResult

        result = PipelineResult(email="User@Example.COM")
        result.checks["syntax"] = CheckResult.pass_(normalized="user@example.com")
        assert result.normalized_email == "user@example.com"

    def test_normalized_email_falls_back_to_raw(self) -> None:
        result = PipelineResult(email="raw@example.com")
        assert result.normalized_email == "raw@example.com"

    def test_mx_records_from_dns_metadata(self) -> None:
        from coldreach.verify._types import CheckResult

        result = PipelineResult(email="user@example.com")
        result.checks["dns"] = CheckResult.pass_(mx_records=["mx1.example.com"])
        assert result.mx_records == ["mx1.example.com"]

    def test_mx_records_empty_when_no_dns_check(self) -> None:
        result = PipelineResult(email="user@example.com")
        assert result.mx_records == []

    def test_failure_reason_returns_first_fail_reason(self) -> None:
        from coldreach.verify._types import CheckResult

        result = PipelineResult(email="bad")
        result.checks["syntax"] = CheckResult.fail("Bad syntax")
        assert result.failure_reason == "Bad syntax"

    def test_failure_reason_none_when_all_pass(self) -> None:
        from coldreach.verify._types import CheckResult

        result = PipelineResult(email="user@example.com")
        result.checks["syntax"] = CheckResult.pass_()
        assert result.failure_reason is None

    def test_to_dict_structure(self) -> None:
        from coldreach.verify._types import CheckResult

        result = PipelineResult(email="user@example.com")
        result.checks["syntax"] = CheckResult.pass_(normalized="user@example.com")
        d = result.to_dict()
        assert "email" in d
        assert "normalized" in d
        assert "passed" in d
        assert "score" in d
        assert "checks" in d
        assert "syntax" in d["checks"]


# ---------------------------------------------------------------------------
# run_basic_pipeline integration (mocked DNS)
# ---------------------------------------------------------------------------


class TestRunBasicPipeline:
    """End-to-end pipeline tests with mocked DNS."""

    @pytest.mark.asyncio
    async def test_valid_email_with_mx_passes(self) -> None:
        answer = [_make_mx_answer("mail.example.com")]
        with patch(
            "coldreach.verify.dns_check.dns.asyncresolver.Resolver.resolve",
            new_callable=AsyncMock,
            return_value=answer,
        ):
            result = await run_basic_pipeline("john@example.com")

        assert result.passed
        assert "syntax" in result.checks
        assert "disposable" in result.checks
        assert "dns" in result.checks

    @pytest.mark.asyncio
    async def test_invalid_syntax_stops_pipeline_early(self) -> None:
        result = await run_basic_pipeline("notanemail")
        assert result.failed
        assert "syntax" in result.checks
        # disposable and dns should not run
        assert "disposable" not in result.checks
        assert "dns" not in result.checks

    @pytest.mark.asyncio
    async def test_disposable_email_stops_pipeline(self) -> None:
        result = await run_basic_pipeline("test@mailinator.com")
        assert result.failed
        assert "syntax" in result.checks
        assert "disposable" in result.checks
        # dns should not run
        assert "dns" not in result.checks

    @pytest.mark.asyncio
    async def test_nxdomain_fails_pipeline(self) -> None:
        with patch(
            "coldreach.verify.dns_check.dns.asyncresolver.Resolver.resolve",
            new_callable=AsyncMock,
            side_effect=dns.resolver.NXDOMAIN,
        ):
            result = await run_basic_pipeline("user@totally-fake-domain-xyz.com")

        assert result.failed

    @pytest.mark.asyncio
    async def test_score_above_baseline_for_clean_email(self) -> None:
        answer = [_make_mx_answer("mail.example.com")]
        with patch(
            "coldreach.verify.dns_check.dns.asyncresolver.Resolver.resolve",
            new_callable=AsyncMock,
            return_value=answer,
        ):
            result = await run_basic_pipeline("john@example.com")

        assert result.score > 30  # above baseline

    @pytest.mark.asyncio
    async def test_score_zero_for_bad_syntax(self) -> None:
        result = await run_basic_pipeline("@@@@")
        assert result.score == 0

    @pytest.mark.asyncio
    async def test_normalized_email_available_after_pass(self) -> None:
        answer = [_make_mx_answer("mail.example.com")]
        with patch(
            "coldreach.verify.dns_check.dns.asyncresolver.Resolver.resolve",
            new_callable=AsyncMock,
            return_value=answer,
        ):
            result = await run_basic_pipeline("John@Example.COM")

        assert result.normalized_email == "john@example.com"

    @pytest.mark.asyncio
    async def test_mx_records_available_after_pass(self) -> None:
        answer = [_make_mx_answer("mx.example.com")]
        with patch(
            "coldreach.verify.dns_check.dns.asyncresolver.Resolver.resolve",
            new_callable=AsyncMock,
            return_value=answer,
        ):
            result = await run_basic_pipeline("user@example.com")

        assert "mx.example.com" in result.mx_records
