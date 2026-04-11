"""
Unit tests for coldreach.sources.harvester

Subprocess calls are mocked — no real theHarvester process.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from coldreach.core.models import EmailSource
from coldreach.sources.harvester import HarvesterSource, _parse_emails


class TestParseEmails:
    def test_extracts_domain_emails(self) -> None:
        output = """
        [*] Emails found: 3
        john@acme.com
        jane@acme.com
        """
        result = _parse_emails(output, "acme.com")
        assert "john@acme.com" in result
        assert "jane@acme.com" in result

    def test_filters_other_domains(self) -> None:
        output = "john@acme.com other@gmail.com"
        result = _parse_emails(output, "acme.com")
        assert "john@acme.com" in result
        assert "other@gmail.com" not in result

    def test_deduplicates(self) -> None:
        output = "john@acme.com john@acme.com"
        result = _parse_emails(output, "acme.com")
        assert result.count("john@acme.com") == 1

    def test_normalises_to_lowercase(self) -> None:
        output = "John@Acme.COM"
        result = _parse_emails(output, "acme.com")
        assert "john@acme.com" in result

    def test_empty_output(self) -> None:
        assert _parse_emails("", "acme.com") == []


class TestHarvesterSource:
    @pytest.mark.asyncio
    async def test_returns_empty_when_not_installed(self) -> None:
        with patch("coldreach.sources.harvester._is_available", return_value=False):
            src = HarvesterSource()
            results = await src.fetch("acme.com")
        assert results == []

    @pytest.mark.asyncio
    async def test_finds_emails_from_subprocess_output(self) -> None:
        stdout = b"john@acme.com\njane@acme.com\n"

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(stdout, b""))

        with (
            patch("coldreach.sources.harvester._is_available", return_value=True),
            patch(
                "coldreach.sources.harvester.asyncio.create_subprocess_exec",
                return_value=mock_proc,
            ),
        ):
            src = HarvesterSource()
            results = await src.fetch("acme.com")

        emails = [r.email for r in results]
        assert "john@acme.com" in emails
        assert "jane@acme.com" in emails
        assert all(r.source == EmailSource.THE_HARVESTER for r in results)

    @pytest.mark.asyncio
    async def test_returns_empty_on_timeout(self) -> None:
        with (
            patch("coldreach.sources.harvester._is_available", return_value=True),
            patch(
                "coldreach.sources.harvester.asyncio.create_subprocess_exec",
                side_effect=TimeoutError,
            ),
        ):
            src = HarvesterSource(timeout=1.0)
            results = await src.fetch("acme.com")

        assert results == []

    @pytest.mark.asyncio
    async def test_returns_empty_on_os_error(self) -> None:
        with (
            patch("coldreach.sources.harvester._is_available", return_value=True),
            patch(
                "coldreach.sources.harvester.asyncio.create_subprocess_exec",
                side_effect=OSError("not found"),
            ),
        ):
            src = HarvesterSource()
            results = await src.fetch("acme.com")

        assert results == []

    def test_source_name(self) -> None:
        assert HarvesterSource().name == "theharvester"
