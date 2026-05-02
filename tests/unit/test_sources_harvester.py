"""
Unit tests for coldreach.sources.harvester

All HTTP calls are mocked with respx — no real network traffic or Docker.
"""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from coldreach.core.models import EmailSource
from coldreach.sources.harvester import _FREE_SOURCES, _VALID_EMAIL_RE, HarvesterSource


def _api_url(src: HarvesterSource) -> str:
    return f"{src.api_base}/query"


def _json_resp(emails: list[str]) -> Response:
    return Response(200, json={"emails": emails, "hosts": [], "ips": []})


# ---------------------------------------------------------------------------
# _filter_emails — pure logic, no network
# ---------------------------------------------------------------------------


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
        src = HarvesterSource()
        result = src._filter_emails(["u003caccount@acme.com"], "acme.com")
        assert result == []

    def test_accepts_subdomain_emails(self) -> None:
        src = HarvesterSource()
        result = src._filter_emails(["hr@us.acme.com"], "acme.com")
        assert "hr@us.acme.com" in result

    def test_empty_input(self) -> None:
        assert HarvesterSource()._filter_emails([], "acme.com") == []


# ---------------------------------------------------------------------------
# _query_api — HTTP calls mocked with respx
# ---------------------------------------------------------------------------


class TestHarvesterSourceQueryApi:
    @pytest.mark.asyncio
    @respx.mock
    async def test_returns_emails_on_200(self) -> None:
        src = HarvesterSource()
        respx.get(_api_url(src)).mock(return_value=_json_resp(["ceo@acme.com", "hr@acme.com"]))
        emails = await src._query_api("acme.com")
        assert "ceo@acme.com" in emails
        assert "hr@acme.com" in emails

    @pytest.mark.asyncio
    @respx.mock
    async def test_filters_to_target_domain(self) -> None:
        src = HarvesterSource()
        respx.get(_api_url(src)).mock(return_value=_json_resp(["ceo@acme.com", "noise@gmail.com"]))
        emails = await src._query_api("acme.com")
        assert "noise@gmail.com" not in emails
        assert "ceo@acme.com" in emails

    @pytest.mark.asyncio
    @respx.mock
    async def test_returns_empty_on_500(self) -> None:
        src = HarvesterSource()
        respx.get(_api_url(src)).mock(return_value=Response(500, text="error"))
        emails = await src._query_api("acme.com")
        assert emails == []

    @pytest.mark.asyncio
    @respx.mock
    async def test_returns_empty_on_empty_email_list(self) -> None:
        src = HarvesterSource()
        respx.get(_api_url(src)).mock(return_value=_json_resp([]))
        emails = await src._query_api("acme.com")
        assert emails == []

    @pytest.mark.asyncio
    @respx.mock
    async def test_returns_empty_on_connect_error(self) -> None:
        import httpx

        src = HarvesterSource()
        respx.get(_api_url(src)).mock(side_effect=httpx.ConnectError("refused"))
        emails = await src._query_api("acme.com")
        assert emails == []

    @pytest.mark.asyncio
    @respx.mock
    async def test_passes_domain_source_limit_params(self) -> None:
        # Sources must be sent as repeated params: source=crtsh&source=duckduckgo
        # NOT as a comma-joined value — the API rejects comma-joined sources.
        src = HarvesterSource(sources="crtsh,duckduckgo", limit=100)
        route = respx.get(_api_url(src)).mock(return_value=_json_resp([]))
        await src._query_api("example.com")
        request = route.calls.last.request
        url_str = str(request.url)
        assert "domain=example.com" in url_str
        # Each source is a separate param (repeated), not comma-joined
        assert "source=crtsh" in url_str
        assert "source=duckduckgo" in url_str
        assert "limit=100" in url_str

    @pytest.mark.asyncio
    @respx.mock
    async def test_handles_missing_emails_key(self) -> None:
        src = HarvesterSource()
        respx.get(_api_url(src)).mock(return_value=Response(200, json={"hosts": [], "ips": []}))
        emails = await src._query_api("acme.com")
        assert emails == []

    @pytest.mark.asyncio
    @respx.mock
    async def test_handles_invalid_json(self) -> None:
        src = HarvesterSource()
        respx.get(_api_url(src)).mock(return_value=Response(200, text="not-json"))
        emails = await src._query_api("acme.com")
        assert emails == []


# ---------------------------------------------------------------------------
# fetch — integration via _query_api mock
# ---------------------------------------------------------------------------


class TestHarvesterSourceFetch:
    @pytest.mark.asyncio
    async def test_returns_source_results(self) -> None:
        src = HarvesterSource()
        with respx.mock:
            respx.get(_api_url(src)).mock(return_value=_json_resp(["cto@acme.com"]))
            results = await src.fetch("acme.com")
        assert len(results) == 1
        assert results[0].email == "cto@acme.com"
        assert results[0].source == EmailSource.THE_HARVESTER

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_emails(self) -> None:
        src = HarvesterSource()
        with respx.mock:
            respx.get(_api_url(src)).mock(return_value=_json_resp([]))
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

    @pytest.mark.asyncio
    async def test_confidence_hint_is_positive(self) -> None:
        src = HarvesterSource()
        with respx.mock:
            respx.get(_api_url(src)).mock(return_value=_json_resp(["info@acme.com"]))
            results = await src.fetch("acme.com")
        assert results[0].confidence_hint > 0


# ---------------------------------------------------------------------------
# Regex helpers
# ---------------------------------------------------------------------------


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
