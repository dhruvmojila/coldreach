"""
Unit tests for coldreach.sources.spiderfoot

SpiderFoot now uses the REST API (localhost:5001) — all HTTP calls are mocked
with respx.  No docker exec, no real container required.
"""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from coldreach.core.models import EmailSource
from coldreach.sources.spiderfoot import SpiderFootSource


def _api(src: SpiderFootSource, path: str) -> str:
    return f"{src.api_base}{path}"


def _rows(*emails: str) -> list[list[str]]:
    return [["EMAILADDR", e, "sfp_pgp"] for e in emails]


# ---------------------------------------------------------------------------
# _parse_output (used by fetch via _fetch_results)
# ---------------------------------------------------------------------------


class TestSpiderFootSourceParseOutput:
    def test_extracts_domain_emails(self) -> None:
        src = SpiderFootSource()
        result = src._parse_output(
            '[["EMAILADDR","john@acme.com","sfp_pgp"],["EMAILADDR","jane@acme.com","sfp_x"]]',
            "acme.com",
        )
        assert "john@acme.com" in result
        assert "jane@acme.com" in result

    def test_filters_other_domains(self) -> None:
        src = SpiderFootSource()
        result = src._parse_output(
            '[["EMAILADDR","noise@gmail.com","sfp_x"],["EMAILADDR","ceo@acme.com","sfp_pgp"]]',
            "acme.com",
        )
        assert "noise@gmail.com" not in result
        assert "ceo@acme.com" in result

    def test_deduplicates(self) -> None:
        src = SpiderFootSource()
        result = src._parse_output(
            '[["EMAILADDR","ceo@acme.com","sfp_a"],["EMAILADDR","ceo@acme.com","sfp_b"]]',
            "acme.com",
        )
        assert result.count("ceo@acme.com") == 1

    def test_handles_email_address_type_string(self) -> None:
        """Accepts both 'EMAILADDR' and 'Email Address' type strings."""
        src = SpiderFootSource()
        result = src._parse_output(
            '[{"type":"Email Address","data":"cto@acme.com","module":"sfp_pgp"}]',
            "acme.com",
        )
        assert "cto@acme.com" in result

    def test_strips_annotation_brackets(self) -> None:
        """Emails like 'user@acme.com [apollo.io]' should be cleaned."""
        src = SpiderFootSource()
        result = src._parse_output(
            '[["EMAILADDR","user@acme.com [apollo.io]","sfp_citadel"]]',
            "acme.com",
        )
        assert "user@acme.com" in result

    def test_returns_empty_for_empty_input(self) -> None:
        src = SpiderFootSource()
        assert src._parse_output("", "acme.com") == []

    def test_handles_partial_json(self) -> None:
        src = SpiderFootSource()
        # Scan killed mid-write — partial JSON should be recovered
        partial = '[["EMAILADDR","ceo@acme.com","sfp_pgp"],["EMAILADDR","cto@acme.com"'
        result = src._parse_output(partial, "acme.com")
        assert "ceo@acme.com" in result


# ---------------------------------------------------------------------------
# REST API helpers — mocked with respx
# ---------------------------------------------------------------------------


class TestSpiderFootRestApi:
    @pytest.mark.asyncio
    @respx.mock
    async def test_is_available_true_on_200(self) -> None:
        src = SpiderFootSource()
        respx.get(_api(src, "/ping")).mock(return_value=Response(200, json=["SUCCESS", "4.0.0"]))
        assert await src._is_available() is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_is_available_false_on_connect_error(self) -> None:
        import httpx

        src = SpiderFootSource()
        respx.get(_api(src, "/ping")).mock(side_effect=httpx.ConnectError("refused"))
        assert await src._is_available() is False

    @pytest.mark.asyncio
    @respx.mock
    async def test_start_scan_returns_scan_id(self) -> None:
        src = SpiderFootSource()
        respx.post(_api(src, "/startscan")).mock(
            return_value=Response(200, json=["SUCCESS", "SCAN123"])
        )
        scan_id = await src._start_scan("acme.com")
        assert scan_id == "SCAN123"

    @pytest.mark.asyncio
    @respx.mock
    async def test_start_scan_returns_none_on_error(self) -> None:
        src = SpiderFootSource()
        respx.post(_api(src, "/startscan")).mock(
            return_value=Response(200, json=["ERROR", "bad target"])
        )
        assert await src._start_scan("acme.com") is None

    @pytest.mark.asyncio
    @respx.mock
    async def test_scan_status_returns_status_string(self) -> None:
        src = SpiderFootSource()
        respx.get(_api(src, "/scanstatus")).mock(
            return_value=Response(
                200, json=["coldreach-acme.com", "acme.com", "2024-01-01", "2024-01-01", "FINISHED"]
            )
        )
        status = await src._scan_status("SCAN123")
        assert status == "FINISHED"

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_results_returns_rows(self) -> None:
        src = SpiderFootSource()
        respx.get(_api(src, "/scaneventresults")).mock(
            return_value=Response(200, json=_rows("ceo@acme.com", "cto@acme.com"))
        )
        rows = await src._fetch_results("SCAN123")
        assert len(rows) == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_stop_scan_called_silently(self) -> None:
        src = SpiderFootSource()
        route = respx.get(_api(src, "/stopscan")).mock(return_value=Response(200, json=["OK"]))
        await src._stop_scan("SCAN123")
        assert route.called


# ---------------------------------------------------------------------------
# fetch — integration via REST API mocks
# ---------------------------------------------------------------------------


class TestSpiderFootSourceFetch:
    @pytest.mark.asyncio
    @respx.mock
    async def test_returns_source_results(self) -> None:
        src = SpiderFootSource()
        respx.get(_api(src, "/ping")).mock(return_value=Response(200, json=["SUCCESS", "4.0.0"]))
        respx.post(_api(src, "/startscan")).mock(
            return_value=Response(200, json=["SUCCESS", "SCAN123"])
        )
        respx.get(_api(src, "/scanstatus")).mock(
            return_value=Response(200, json=["test", "acme.com", "", "", "FINISHED"])
        )
        respx.get(_api(src, "/scaneventresults")).mock(
            return_value=Response(200, json=_rows("ceo@acme.com"))
        )
        respx.get(_api(src, "/stopscan")).mock(return_value=Response(200, json=["OK"]))

        results = await src.fetch("acme.com")
        assert len(results) == 1
        assert results[0].email == "ceo@acme.com"
        assert results[0].source == EmailSource.SPIDERFOOT

    @pytest.mark.asyncio
    @respx.mock
    async def test_returns_empty_when_unavailable(self) -> None:
        import httpx

        src = SpiderFootSource()
        respx.get(_api(src, "/ping")).mock(side_effect=httpx.ConnectError("refused"))
        results = await src.fetch("acme.com")
        assert results == []

    def test_source_name(self) -> None:
        assert SpiderFootSource().name == "spiderfoot"

    @pytest.mark.asyncio
    @respx.mock
    async def test_confidence_hint_is_positive(self) -> None:
        src = SpiderFootSource()
        respx.get(_api(src, "/ping")).mock(return_value=Response(200, json=["SUCCESS", "4.0.0"]))
        respx.post(_api(src, "/startscan")).mock(
            return_value=Response(200, json=["SUCCESS", "SCAN456"])
        )
        respx.get(_api(src, "/scanstatus")).mock(
            return_value=Response(200, json=["test", "acme.com", "", "", "FINISHED"])
        )
        respx.get(_api(src, "/scaneventresults")).mock(
            return_value=Response(200, json=_rows("info@acme.com"))
        )
        respx.get(_api(src, "/stopscan")).mock(return_value=Response(200, json=["OK"]))

        results = await src.fetch("acme.com")
        assert results[0].confidence_hint > 0
