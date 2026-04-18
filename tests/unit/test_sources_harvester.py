"""
Unit tests for coldreach.sources.harvester

docker exec / subprocess calls are mocked — no real container required.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from coldreach.core.models import EmailSource
from coldreach.sources.harvester import _FREE_SOURCES, _VALID_EMAIL_RE, HarvesterSource


def _make_proc(stdout: bytes, stderr: bytes = b"", returncode: int = 0) -> MagicMock:
    proc = MagicMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    proc.kill = MagicMock()
    return proc


def _json_file(emails: list[str]) -> bytes:
    return json.dumps({"emails": emails, "hosts": [], "shodan": []}).encode()


class TestHarvesterSourceFilterEmails:
    def test_keeps_domain_emails(self) -> None:
        src = HarvesterSource()
        result = src._filter_emails(["john@acme.com", "jane@acme.com"], "acme.com")
        assert "john@acme.com" in result
        assert "jane@acme.com" in result

    def test_removes_other_domains(self) -> None:
        src = HarvesterSource()
        result = src._filter_emails(["john@acme.com", "spam@gmail.com"], "acme.com")
        assert "spam@gmail.com" not in result

    def test_deduplicates(self) -> None:
        src = HarvesterSource()
        result = src._filter_emails(["john@acme.com", "john@acme.com"], "acme.com")
        assert result.count("john@acme.com") == 1

    def test_normalises_to_lowercase(self) -> None:
        src = HarvesterSource()
        result = src._filter_emails(["JOHN@ACME.COM"], "acme.com")
        assert "john@acme.com" in result

    def test_rejects_html_encoded_emails(self) -> None:
        # theHarvester sometimes emits u003c<account@domain which is invalid
        src = HarvesterSource()
        result = src._filter_emails(["u003caccount@acme.com"], "acme.com")
        assert result == []

    def test_accepts_subdomain_emails(self) -> None:
        src = HarvesterSource()
        result = src._filter_emails(["hr@us.acme.com"], "acme.com")
        assert "hr@us.acme.com" in result

    def test_empty_input(self) -> None:
        assert HarvesterSource()._filter_emails([], "acme.com") == []


class TestHarvesterSourceRunCli:
    @pytest.mark.asyncio
    async def test_returns_emails_on_success(self) -> None:
        harvest_proc = _make_proc(b"", b"", returncode=0)
        read_proc = _make_proc(_json_file(["ceo@acme.com", "hr@acme.com"]))

        call_count = 0

        async def fake_exec(*args: object, **kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            return harvest_proc if call_count == 1 else read_proc

        with patch("asyncio.create_subprocess_exec", side_effect=fake_exec):
            src = HarvesterSource()
            emails = await src._run_cli("acme.com")

        assert "ceo@acme.com" in emails
        assert "hr@acme.com" in emails

    @pytest.mark.asyncio
    async def test_returns_empty_when_docker_not_found(self) -> None:
        with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError):
            src = HarvesterSource()
            emails = await src._run_cli("acme.com")
        assert emails == []

    @pytest.mark.asyncio
    async def test_returns_empty_on_nonzero_exit(self) -> None:
        proc = _make_proc(b"", b"No such container: coldreach-theharvester", returncode=1)
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            src = HarvesterSource()
            emails = await src._run_cli("acme.com")
        assert emails == []

    @pytest.mark.asyncio
    async def test_kills_process_on_timeout(self) -> None:
        import asyncio as _asyncio

        proc = MagicMock()
        proc.returncode = None
        proc.kill = MagicMock()

        async def hang() -> tuple[bytes, bytes]:
            await _asyncio.sleep(9999)
            return b"", b""

        proc.communicate = hang

        with patch("asyncio.create_subprocess_exec", return_value=proc):
            src = HarvesterSource(max_wait=0.01)
            emails = await src._run_cli("acme.com")

        assert emails == []
        proc.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_empty_on_os_error(self) -> None:
        with patch("asyncio.create_subprocess_exec", side_effect=OSError("perm denied")):
            src = HarvesterSource()
            emails = await src._run_cli("acme.com")
        assert emails == []


class TestHarvesterSourceFetch:
    @pytest.mark.asyncio
    async def test_returns_source_results(self) -> None:
        src = HarvesterSource()
        with patch.object(src, "_run_cli", return_value=["cto@acme.com"]):
            results = await src.fetch("acme.com")
        assert len(results) == 1
        assert results[0].email == "cto@acme.com"
        assert results[0].source == EmailSource.THE_HARVESTER

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_emails(self) -> None:
        src = HarvesterSource()
        with patch.object(src, "_run_cli", return_value=[]):
            results = await src.fetch("acme.com")
        assert results == []

    def test_source_name(self) -> None:
        assert HarvesterSource().name == "theharvester"

    def test_default_sources_are_free_sources(self) -> None:
        src = HarvesterSource()
        assert src.sources == ",".join(_FREE_SOURCES)

    def test_custom_sources_string(self) -> None:
        src = HarvesterSource(sources="all")
        assert src.sources == "all"

    def test_confidence_hint_is_positive(self) -> None:
        import asyncio

        src = HarvesterSource()
        with patch.object(src, "_run_cli", return_value=["info@acme.com"]):
            results = asyncio.run(src.fetch("acme.com"))
        assert results[0].confidence_hint > 0


class TestValidEmailRegex:
    def test_valid_email(self) -> None:
        assert _VALID_EMAIL_RE.match("john@acme.com")

    def test_rejects_no_at(self) -> None:
        assert not _VALID_EMAIL_RE.match("notanemail")


class TestHtmlEntityPrefixRegex:
    def test_rejects_u003c_prefix(self) -> None:
        from coldreach.sources.harvester import _HTML_ENTITY_PREFIX_RE

        assert _HTML_ENTITY_PREFIX_RE.match("u003caccount")

    def test_rejects_u002f_prefix(self) -> None:
        from coldreach.sources.harvester import _HTML_ENTITY_PREFIX_RE

        assert _HTML_ENTITY_PREFIX_RE.match("u002fbusiness")

    def test_accepts_normal_user(self) -> None:
        from coldreach.sources.harvester import _HTML_ENTITY_PREFIX_RE

        assert not _HTML_ENTITY_PREFIX_RE.match("utility")
        assert not _HTML_ENTITY_PREFIX_RE.match("user123")
