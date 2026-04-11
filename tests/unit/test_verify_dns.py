"""
Unit tests for coldreach.verify.dns_check

DNS calls are mocked — no real network traffic.
Uses unittest.mock to patch dns.asyncresolver.Resolver.resolve.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import dns.exception
import dns.resolver
import pytest

from coldreach.verify._types import CheckStatus
from coldreach.verify.dns_check import check_dns, domain_exists, get_mx_records

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mx_answer(hostname: str, preference: int = 10) -> MagicMock:
    """Build a mock MX resource record."""
    rdata = MagicMock()
    rdata.preference = preference
    rdata.exchange = MagicMock()
    rdata.exchange.__str__ = lambda self: f"{hostname}."
    return rdata


# ---------------------------------------------------------------------------
# get_mx_records
# ---------------------------------------------------------------------------


class TestGetMxRecords:
    """Tests for the raw get_mx_records() helper."""

    @pytest.mark.asyncio
    async def test_returns_mx_hostnames_on_success(self) -> None:
        answer = [_make_mx_answer("mail.example.com", preference=10)]

        with patch(
            "coldreach.verify.dns_check.dns.asyncresolver.Resolver.resolve",
            new_callable=AsyncMock,
            return_value=answer,
        ):
            records = await get_mx_records("example.com")

        assert records == ["mail.example.com"]

    @pytest.mark.asyncio
    async def test_sorts_by_preference_ascending(self) -> None:
        answer = [
            _make_mx_answer("mx2.example.com", preference=20),
            _make_mx_answer("mx1.example.com", preference=10),
        ]

        with patch(
            "coldreach.verify.dns_check.dns.asyncresolver.Resolver.resolve",
            new_callable=AsyncMock,
            return_value=answer,
        ):
            records = await get_mx_records("example.com")

        assert records == ["mx1.example.com", "mx2.example.com"]

    @pytest.mark.asyncio
    async def test_trailing_dot_stripped_from_hostname(self) -> None:
        answer = [_make_mx_answer("mail.example.com.", preference=10)]

        with patch(
            "coldreach.verify.dns_check.dns.asyncresolver.Resolver.resolve",
            new_callable=AsyncMock,
            return_value=answer,
        ):
            records = await get_mx_records("example.com")

        assert records[0] == "mail.example.com"
        assert not records[0].endswith(".")

    @pytest.mark.asyncio
    async def test_nxdomain_returns_empty_list(self) -> None:
        with patch(
            "coldreach.verify.dns_check.dns.asyncresolver.Resolver.resolve",
            new_callable=AsyncMock,
            side_effect=dns.resolver.NXDOMAIN,
        ):
            records = await get_mx_records("this-domain-does-not-exist-xyzabc.com")

        assert records == []

    @pytest.mark.asyncio
    async def test_no_answer_returns_empty_list(self) -> None:
        with patch(
            "coldreach.verify.dns_check.dns.asyncresolver.Resolver.resolve",
            new_callable=AsyncMock,
            side_effect=dns.resolver.NoAnswer,
        ):
            records = await get_mx_records("example.com")

        assert records == []

    @pytest.mark.asyncio
    async def test_dns_timeout_returns_empty_list(self) -> None:
        with patch(
            "coldreach.verify.dns_check.dns.asyncresolver.Resolver.resolve",
            new_callable=AsyncMock,
            side_effect=dns.exception.Timeout,
        ):
            records = await get_mx_records("example.com")

        assert records == []


# ---------------------------------------------------------------------------
# domain_exists
# ---------------------------------------------------------------------------


class TestDomainExists:
    """Tests for the domain_exists() A/AAAA record fallback checker."""

    @pytest.mark.asyncio
    async def test_returns_true_when_a_record_found(self) -> None:
        with patch(
            "coldreach.verify.dns_check.dns.asyncresolver.Resolver.resolve",
            new_callable=AsyncMock,
            return_value=[MagicMock()],
        ):
            assert await domain_exists("example.com") is True

    @pytest.mark.asyncio
    async def test_returns_false_when_nxdomain(self) -> None:
        with patch(
            "coldreach.verify.dns_check.dns.asyncresolver.Resolver.resolve",
            new_callable=AsyncMock,
            side_effect=dns.resolver.NXDOMAIN,
        ):
            assert await domain_exists("not-a-real-domain-xyzabc.com") is False


# ---------------------------------------------------------------------------
# check_dns (pipeline checker)
# ---------------------------------------------------------------------------


class TestCheckDns:
    """Tests for the pipeline-level check_dns() function."""

    @pytest.mark.asyncio
    async def test_passes_when_mx_records_found(self) -> None:
        answer = [_make_mx_answer("mail.example.com")]

        with patch(
            "coldreach.verify.dns_check.dns.asyncresolver.Resolver.resolve",
            new_callable=AsyncMock,
            return_value=answer,
        ):
            result = await check_dns("user@example.com")

        assert result.passed

    @pytest.mark.asyncio
    async def test_mx_records_in_metadata_on_pass(self) -> None:
        answer = [_make_mx_answer("mail.example.com")]

        with patch(
            "coldreach.verify.dns_check.dns.asyncresolver.Resolver.resolve",
            new_callable=AsyncMock,
            return_value=answer,
        ):
            result = await check_dns("user@example.com")

        assert "mx_records" in result.metadata
        assert result.metadata["mx_records"] == ["mail.example.com"]

    @pytest.mark.asyncio
    async def test_positive_score_delta_on_pass(self) -> None:
        answer = [_make_mx_answer("mail.example.com")]

        with patch(
            "coldreach.verify.dns_check.dns.asyncresolver.Resolver.resolve",
            new_callable=AsyncMock,
            return_value=answer,
        ):
            result = await check_dns("user@example.com")

        assert result.score_delta > 0

    @pytest.mark.asyncio
    async def test_fails_when_no_mx_and_no_a_record(self) -> None:
        with patch(
            "coldreach.verify.dns_check.dns.asyncresolver.Resolver.resolve",
            new_callable=AsyncMock,
            side_effect=dns.resolver.NXDOMAIN,
        ):
            result = await check_dns("user@nonexistent-xyz-abc.com")

        assert result.failed

    @pytest.mark.asyncio
    async def test_negative_score_delta_on_fail(self) -> None:
        with patch(
            "coldreach.verify.dns_check.dns.asyncresolver.Resolver.resolve",
            new_callable=AsyncMock,
            side_effect=dns.resolver.NXDOMAIN,
        ):
            result = await check_dns("user@nonexistent-xyz-abc.com")

        assert result.score_delta < 0

    @pytest.mark.asyncio
    async def test_warns_when_no_mx_but_a_record_exists(self) -> None:
        # First resolve (MX) raises NoAnswer, second (A) returns something
        call_count = 0

        async def side_effect(*args: Any, **kwargs: Any) -> Any:
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # MX lookup
                raise dns.resolver.NoAnswer
            return [MagicMock()]  # A record exists

        with patch(
            "coldreach.verify.dns_check.dns.asyncresolver.Resolver.resolve",
            new_callable=AsyncMock,
            side_effect=side_effect,
        ):
            result = await check_dns("user@example.com")

        assert result.status == CheckStatus.WARN

    @pytest.mark.asyncio
    async def test_fails_on_empty_email(self) -> None:
        result = await check_dns("")
        assert result.failed

    @pytest.mark.asyncio
    async def test_fails_on_email_without_domain(self) -> None:
        result = await check_dns("user@")
        assert result.failed

    @pytest.mark.asyncio
    async def test_domain_in_metadata_on_pass(self) -> None:
        answer = [_make_mx_answer("mail.example.com")]

        with patch(
            "coldreach.verify.dns_check.dns.asyncresolver.Resolver.resolve",
            new_callable=AsyncMock,
            return_value=answer,
        ):
            result = await check_dns("user@example.com")

        assert result.metadata.get("domain") == "example.com"
