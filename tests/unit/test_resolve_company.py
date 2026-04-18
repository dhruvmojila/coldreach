"""
Unit tests for coldreach.resolve.company

All HTTP calls are mocked with respx — no real network traffic.
"""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from coldreach.resolve.company import (
    _extract_domain_from_ddg_html,
    resolve_domain,
)


class TestResolveViaClearbit:
    @pytest.mark.asyncio
    @respx.mock
    async def test_returns_domain_on_success(self) -> None:
        respx.get("https://autocomplete.clearbit.com/v1/companies/suggest").mock(
            return_value=Response(
                200,
                json=[{"name": "Stripe", "domain": "stripe.com", "logo": ""}],
            )
        )
        result = await resolve_domain("Stripe")
        assert result == "stripe.com"

    @pytest.mark.asyncio
    @respx.mock
    async def test_returns_first_result(self) -> None:
        respx.get("https://autocomplete.clearbit.com/v1/companies/suggest").mock(
            return_value=Response(
                200,
                json=[
                    {"name": "Acme Corp", "domain": "acme.com"},
                    {"name": "Acme Inc", "domain": "acmeinc.com"},
                ],
            )
        )
        result = await resolve_domain("Acme")
        assert result == "acme.com"

    @pytest.mark.asyncio
    @respx.mock
    async def test_lowercases_domain(self) -> None:
        respx.get("https://autocomplete.clearbit.com/v1/companies/suggest").mock(
            return_value=Response(200, json=[{"name": "Test", "domain": "Test.COM"}])
        )
        result = await resolve_domain("Test")
        assert result == "test.com"

    @pytest.mark.asyncio
    @respx.mock
    async def test_returns_none_on_empty_response(self) -> None:
        respx.get("https://autocomplete.clearbit.com/v1/companies/suggest").mock(
            return_value=Response(200, json=[])
        )
        # DDG also mocked to fail so we get None
        respx.post("https://duckduckgo.com/lite/").mock(return_value=Response(500, text=""))
        result = await resolve_domain("UnknownXYZ123")
        assert result is None

    @pytest.mark.asyncio
    @respx.mock
    async def test_returns_none_on_http_error(self) -> None:
        respx.get("https://autocomplete.clearbit.com/v1/companies/suggest").mock(
            return_value=Response(500, text="")
        )
        respx.post("https://duckduckgo.com/lite/").mock(return_value=Response(500, text=""))
        result = await resolve_domain("Stripe")
        assert result is None


class TestResolveViaDDGFallback:
    @pytest.mark.asyncio
    @respx.mock
    async def test_falls_back_to_ddg_when_clearbit_empty(self) -> None:
        respx.get("https://autocomplete.clearbit.com/v1/companies/suggest").mock(
            return_value=Response(200, json=[])
        )
        ddg_html = (
            "<html><body>"
            '<a class="result-link" href="https://www.acme.com/about">Acme</a>'
            "</body></html>"
        )
        respx.post("https://duckduckgo.com/lite/").mock(return_value=Response(200, text=ddg_html))
        result = await resolve_domain("Acme Corp")
        assert result == "acme.com"

    @pytest.mark.asyncio
    @respx.mock
    async def test_ddg_strips_www_prefix(self) -> None:
        respx.get("https://autocomplete.clearbit.com/v1/companies/suggest").mock(
            return_value=Response(200, json=[])
        )
        ddg_html = '<a href="https://www.example.com/page">text</a>'
        respx.post("https://duckduckgo.com/lite/").mock(return_value=Response(200, text=ddg_html))
        result = await resolve_domain("Example Co")
        assert result == "example.com"

    @pytest.mark.asyncio
    @respx.mock
    async def test_ddg_skips_noise_domains(self) -> None:
        respx.get("https://autocomplete.clearbit.com/v1/companies/suggest").mock(
            return_value=Response(200, json=[])
        )
        # First link is LinkedIn (noise), second is the real site
        ddg_html = (
            '<a href="https://www.linkedin.com/company/acme">LinkedIn</a>'
            '<a href="https://www.acme.io/home">Acme</a>'
        )
        respx.post("https://duckduckgo.com/lite/").mock(return_value=Response(200, text=ddg_html))
        result = await resolve_domain("Acme")
        assert result == "acme.io"


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_returns_none_for_empty_string(self) -> None:
        result = await resolve_domain("")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_for_whitespace_only(self) -> None:
        result = await resolve_domain("   ")
        assert result is None


class TestExtractDomainFromDDGHtml:
    def test_extracts_first_valid_domain(self) -> None:
        html = '<a href="https://stripe.com/about">Stripe</a>'
        assert _extract_domain_from_ddg_html(html) == "stripe.com"

    def test_strips_www(self) -> None:
        html = '<a href="https://www.stripe.com/about">Stripe</a>'
        assert _extract_domain_from_ddg_html(html) == "stripe.com"

    def test_skips_duckduckgo_links(self) -> None:
        html = (
            '<a href="https://duckduckgo.com/y.js?f=1">DDG</a>'
            '<a href="https://stripe.com">Stripe</a>'
        )
        assert _extract_domain_from_ddg_html(html) == "stripe.com"

    def test_skips_noise_domains(self) -> None:
        html = (
            '<a href="https://linkedin.com/company/stripe">LinkedIn</a>'
            '<a href="https://stripe.com">Stripe</a>'
        )
        assert _extract_domain_from_ddg_html(html) == "stripe.com"

    def test_returns_none_when_no_valid_link(self) -> None:
        html = '<a href="https://linkedin.com/company/x">LinkedIn</a>'
        assert _extract_domain_from_ddg_html(html) is None

    def test_returns_none_for_empty_html(self) -> None:
        assert _extract_domain_from_ddg_html("") is None
