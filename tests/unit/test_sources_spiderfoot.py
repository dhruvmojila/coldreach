"""
Unit tests for coldreach.sources.spiderfoot

docker exec / subprocess calls are mocked — no real container required.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from coldreach.core.models import EmailSource
from coldreach.sources.spiderfoot import SpiderFootSource


def _make_proc(stdout: bytes, stderr: bytes = b"", returncode: int = 0) -> MagicMock:
    proc = MagicMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    proc.kill = MagicMock()
    return proc


def _json_rows(emails: list[str]) -> bytes:
    rows = [["EMAILADDR", e, "sfp_hunter"] for e in emails]
    return json.dumps(rows).encode()


class TestSpiderFootSourceParseOutput:
    def test_extracts_domain_emails(self) -> None:
        src = SpiderFootSource()
        rows = json.dumps(
            [["EMAILADDR", "john@acme.com", "sfp_hunter"], ["EMAILADDR", "jane@acme.com", "sfp_x"]]
        )
        result = src._parse_output(rows, "acme.com")
        assert "john@acme.com" in result
        assert "jane@acme.com" in result

    def test_filters_other_domains(self) -> None:
        src = SpiderFootSource()
        rows = json.dumps(
            [["EMAILADDR", "john@acme.com", "x"], ["EMAILADDR", "spam@gmail.com", "x"]]
        )
        result = src._parse_output(rows, "acme.com")
        assert "spam@gmail.com" not in result

    def test_deduplicates(self) -> None:
        src = SpiderFootSource()
        rows = json.dumps(
            [["EMAILADDR", "john@acme.com", "x"], ["EMAILADDR", "john@acme.com", "y"]]
        )
        result = src._parse_output(rows, "acme.com")
        assert result.count("john@acme.com") == 1

    def test_normalises_to_lowercase(self) -> None:
        src = SpiderFootSource()
        rows = json.dumps([["EMAILADDR", "JOHN@ACME.COM", "x"]])
        result = src._parse_output(rows, "acme.com")
        assert "john@acme.com" in result

    def test_ignores_non_emailaddr_events(self) -> None:
        src = SpiderFootSource()
        rows = json.dumps(
            [["INTERNET_NAME", "mail.acme.com", "x"], ["EMAILADDR", "info@acme.com", "x"]]
        )
        result = src._parse_output(rows, "acme.com")
        assert result == ["info@acme.com"]

    def test_handles_dict_row_format(self) -> None:
        src = SpiderFootSource()
        rows = json.dumps([{"type": "EMAILADDR", "data": "cto@acme.com"}])
        result = src._parse_output(rows, "acme.com")
        assert "cto@acme.com" in result

    def test_returns_empty_on_bad_json(self) -> None:
        src = SpiderFootSource()
        result = src._parse_output("not json", "acme.com")
        assert result == []

    def test_returns_empty_on_empty_output(self) -> None:
        src = SpiderFootSource()
        result = src._parse_output("", "acme.com")
        assert result == []

    def test_accepts_subdomain_emails(self) -> None:
        src = SpiderFootSource()
        rows = json.dumps([["EMAILADDR", "hr@us.acme.com", "x"]])
        result = src._parse_output(rows, "acme.com")
        assert "hr@us.acme.com" in result


class TestSpiderFootSourceRunCli:
    @pytest.mark.asyncio
    async def test_returns_emails_on_success(self) -> None:
        proc = _make_proc(_json_rows(["ceo@acme.com", "hr@acme.com"]))
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            src = SpiderFootSource()
            emails = await src._run_cli("acme.com")
        assert "ceo@acme.com" in emails
        assert "hr@acme.com" in emails

    @pytest.mark.asyncio
    async def test_returns_empty_when_docker_not_found(self) -> None:
        with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError):
            src = SpiderFootSource()
            emails = await src._run_cli("acme.com")
        assert emails == []

    @pytest.mark.asyncio
    async def test_returns_empty_on_nonzero_exit(self) -> None:
        proc = _make_proc(b"", b"Error response from daemon: No such container", returncode=1)
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            src = SpiderFootSource()
            emails = await src._run_cli("acme.com")
        assert emails == []

    @pytest.mark.asyncio
    async def test_kills_process_on_timeout(self) -> None:
        proc = MagicMock()
        proc.returncode = None
        proc.kill = MagicMock()

        async def hang() -> tuple[bytes, bytes]:
            await asyncio.sleep(9999)
            return b"", b""

        proc.communicate = hang

        with patch("asyncio.create_subprocess_exec", return_value=proc):
            src = SpiderFootSource(max_wait=0.01)
            emails = await src._run_cli("acme.com")

        assert emails == []
        proc.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_empty_on_os_error(self) -> None:
        with patch("asyncio.create_subprocess_exec", side_effect=OSError("perm denied")):
            src = SpiderFootSource()
            emails = await src._run_cli("acme.com")
        assert emails == []


class TestSpiderFootSourceFetch:
    @pytest.mark.asyncio
    async def test_returns_source_results(self) -> None:
        src = SpiderFootSource()
        with patch.object(src, "_run_cli", return_value=["cto@acme.com"]):
            results = await src.fetch("acme.com")
        assert len(results) == 1
        assert results[0].email == "cto@acme.com"
        assert results[0].source == EmailSource.SPIDERFOOT

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_emails(self) -> None:
        src = SpiderFootSource()
        with patch.object(src, "_run_cli", return_value=[]):
            results = await src.fetch("acme.com")
        assert results == []

    def test_source_name(self) -> None:
        assert SpiderFootSource().name == "spiderfoot"

    def test_custom_container(self) -> None:
        src = SpiderFootSource(container="my-spiderfoot")
        assert src.container == "my-spiderfoot"

    def test_confidence_hint_is_positive(self) -> None:
        src = SpiderFootSource()
        with patch.object(src, "_run_cli", return_value=["info@acme.com"]):
            results = asyncio.run(src.fetch("acme.com"))
        assert results[0].confidence_hint > 0
