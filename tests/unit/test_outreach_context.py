"""
Unit tests for coldreach.outreach.context

All HTTP calls mocked with respx — no real network traffic.
"""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from coldreach.outreach.context import (
    CompanyContext,
    _parse_context,
    _strip_html,
    get_company_context,
)


class TestStripHtml:
    def test_removes_tags(self) -> None:
        assert _strip_html("<p>Hello world</p>") == "Hello world"

    def test_removes_scripts(self) -> None:
        result = _strip_html("<script>alert('x')</script>Some text")
        assert "alert" not in result
        assert "Some text" in result

    def test_removes_styles(self) -> None:
        result = _strip_html("<style>.cls{color:red}</style>text")
        assert "color" not in result

    def test_collapses_whitespace(self) -> None:
        result = _strip_html("a    b\n\n\nc")
        assert "  " not in result

    def test_empty_string(self) -> None:
        assert _strip_html("") == ""


class TestParseContext:
    def test_returns_company_context(self) -> None:
        ctx = _parse_context("stripe.com", "Stripe", "Payment infrastructure for the internet.")
        assert isinstance(ctx, CompanyContext)
        assert ctx.domain == "stripe.com"
        assert ctx.name == "Stripe"

    def test_detects_fintech_industry(self) -> None:
        ctx = _parse_context("stripe.com", "Stripe", "payments API for fintech startups")
        assert ctx.industry == "fintech"

    def test_detects_ecommerce_industry(self) -> None:
        ctx = _parse_context("shopify.com", "Shopify", "online store and retail marketplace")
        assert ctx.industry == "e-commerce"

    def test_detects_saas_industry(self) -> None:
        ctx = _parse_context("atlassian.com", "Atlassian", "software platform for developer tools")
        assert ctx.industry == "SaaS"

    def test_no_industry_when_generic(self) -> None:
        ctx = _parse_context("example.com", "Example", "a company that does things")
        assert ctx.industry == ""

    def test_description_from_first_sentences(self) -> None:
        text = "We build payments. We serve millions. We love code. Extra sentence."
        ctx = _parse_context("co.com", "Co", text)
        assert "We build payments" in ctx.description

    def test_raw_text_stored(self) -> None:
        ctx = _parse_context("co.com", "Co", "some raw text")
        assert ctx.raw_text == "some raw text"


class TestGetCompanyContext:
    @pytest.mark.asyncio
    @respx.mock
    async def test_returns_context_from_homepage(self) -> None:
        # Must be > 200 chars to pass the content quality check
        long_text = (
            "<title>Stripe | Payments</title>"
            "<p>Financial infrastructure for the internet. "
            "Stripe provides payment APIs used by millions of businesses. "
            "Founded in 2010, Stripe processes hundreds of billions of dollars. "
            "Based in San Francisco, California. Serving over 120 countries.</p>"
        )
        respx.get("https://stripe.com").mock(return_value=Response(200, text=long_text))
        ctx = await get_company_context("stripe.com")
        assert ctx.domain == "stripe.com"
        assert isinstance(ctx.name, str)
        assert len(ctx.raw_text) > 0

    @pytest.mark.asyncio
    @respx.mock
    async def test_falls_back_to_about_page(self) -> None:
        import httpx

        respx.get("https://stripe.com").mock(side_effect=httpx.ConnectError("refused"))
        respx.get("https://stripe.com/about").mock(
            return_value=Response(200, text="<p>About Stripe: payments company.</p>")
        )
        ctx = await get_company_context("stripe.com")
        assert ctx.domain == "stripe.com"

    @pytest.mark.asyncio
    @respx.mock
    async def test_returns_fallback_when_all_fail(self) -> None:
        import httpx

        # All httpx calls fail
        respx.get("https://stripe.com").mock(side_effect=httpx.ConnectError("refused"))
        respx.get("https://stripe.com/about").mock(side_effect=httpx.ConnectError("refused"))
        respx.get("https://stripe.com/about-us").mock(side_effect=httpx.ConnectError("refused"))
        respx.get("https://stripe.com/company").mock(side_effect=httpx.ConnectError("refused"))
        # SearXNG also fails
        respx.get("http://localhost:8088/search").mock(side_effect=httpx.ConnectError("refused"))
        ctx = await get_company_context("stripe.com")
        # Should not raise — returns minimal context
        assert ctx.domain == "stripe.com"


class TestCompanyContextToPromptContext:
    def test_formats_cleanly(self) -> None:
        ctx = CompanyContext(
            domain="stripe.com",
            name="Stripe",
            description="Financial infrastructure for the internet.",
            industry="fintech",
            location="San Francisco, CA",
            recent_highlights="",
            raw_text="",
        )
        prompt = ctx.to_prompt_context()
        assert "Stripe" in prompt
        assert "stripe.com" in prompt
        assert "fintech" in prompt
        assert len(prompt) <= 1500

    def test_handles_empty_fields(self) -> None:
        ctx = CompanyContext(
            domain="x.com",
            name="X",
            description="",
            industry="",
            location="",
            recent_highlights="",
            raw_text="",
        )
        prompt = ctx.to_prompt_context()
        assert "x.com" in prompt
