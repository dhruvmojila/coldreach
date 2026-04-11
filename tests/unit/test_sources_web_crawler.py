"""
Unit tests for coldreach.sources.web_crawler

All HTTP calls are mocked — no real network traffic.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from coldreach.core.models import EmailSource
from coldreach.sources.web_crawler import (
    WebCrawlerSource,
    _belongs_to_domain,
    _classify_path,
    _extract_emails,
)

# ---------------------------------------------------------------------------
# _belongs_to_domain
# ---------------------------------------------------------------------------


class TestBelongsToDomain:
    def test_exact_match(self) -> None:
        assert _belongs_to_domain("hello@example.com", "example.com") is True

    def test_subdomain_match(self) -> None:
        assert _belongs_to_domain("hello@mail.example.com", "example.com") is True

    def test_different_domain(self) -> None:
        assert _belongs_to_domain("hello@other.com", "example.com") is False

    def test_no_at_sign(self) -> None:
        assert _belongs_to_domain("notanemail", "example.com") is False

    def test_partial_domain_no_match(self) -> None:
        # "notexample.com" should NOT match "example.com"
        assert _belongs_to_domain("x@notexample.com", "example.com") is False


# ---------------------------------------------------------------------------
# _classify_path
# ---------------------------------------------------------------------------


class TestClassifyPath:
    def test_contact_path(self) -> None:
        assert _classify_path("/contact") == EmailSource.WEBSITE_CONTACT

    def test_contact_us_path(self) -> None:
        assert _classify_path("/contact-us") == EmailSource.WEBSITE_CONTACT

    def test_team_path(self) -> None:
        assert _classify_path("/team") == EmailSource.WEBSITE_TEAM

    def test_about_path(self) -> None:
        assert _classify_path("/about") == EmailSource.WEBSITE_ABOUT

    def test_people_path(self) -> None:
        assert _classify_path("/people") == EmailSource.WEBSITE_TEAM

    def test_unknown_path_is_generic(self) -> None:
        assert _classify_path("/pricing") == EmailSource.WEBSITE_GENERIC

    def test_case_insensitive(self) -> None:
        assert _classify_path("/Contact") == EmailSource.WEBSITE_CONTACT


# ---------------------------------------------------------------------------
# _extract_emails
# ---------------------------------------------------------------------------


class TestExtractEmails:
    def test_plain_email_in_text(self) -> None:
        html = "Contact us at hello@example.com for support"
        assert "hello@example.com" in _extract_emails(html, "example.com")

    def test_mailto_link(self) -> None:
        html = '<a href="mailto:sales@example.com">Email us</a>'
        assert "sales@example.com" in _extract_emails(html, "example.com")

    def test_obfuscated_at_bracket(self) -> None:
        html = "reach us: info [at] example.com"
        result = _extract_emails(html, "example.com")
        assert "info@example.com" in result

    def test_obfuscated_at_paren(self) -> None:
        html = "reach us: info(at)example.com"
        result = _extract_emails(html, "example.com")
        assert "info@example.com" in result

    def test_filters_other_domains(self) -> None:
        html = "contact@example.com and other@gmail.com"
        result = _extract_emails(html, "example.com")
        assert "contact@example.com" in result
        assert "other@gmail.com" not in result

    def test_deduplicates_emails(self) -> None:
        html = "hello@example.com hello@example.com"
        result = _extract_emails(html, "example.com")
        assert result.count("hello@example.com") == 1

    def test_normalises_to_lowercase(self) -> None:
        html = "Hello@Example.COM"
        result = _extract_emails(html, "example.com")
        assert "hello@example.com" in result

    def test_ignores_image_extensions(self) -> None:
        html = "icon@2x.png some text"
        result = _extract_emails(html, "2x.png")
        assert result == []

    def test_subdomain_email_included(self) -> None:
        html = "dev@mail.example.com"
        result = _extract_emails(html, "example.com")
        assert "dev@mail.example.com" in result


# ---------------------------------------------------------------------------
# WebCrawlerSource.fetch — mocked HTTP
# ---------------------------------------------------------------------------


def _mock_response(text: str = "", status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    return resp


class TestWebCrawlerFetch:
    @pytest.mark.asyncio
    async def test_finds_email_on_homepage(self) -> None:
        html = '<a href="mailto:ceo@example.com">Contact</a>'

        with patch("coldreach.sources.web_crawler.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=_mock_response(html))
            mock_client_cls.return_value = mock_client

            src = WebCrawlerSource(follow_homepage_links=False)
            results = await src.fetch("example.com")

        emails = [r.email for r in results]
        assert "ceo@example.com" in emails

    @pytest.mark.asyncio
    async def test_returns_empty_on_http_error(self) -> None:
        with patch("coldreach.sources.web_crawler.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=_mock_response("", status_code=404))
            mock_client_cls.return_value = mock_client

            src = WebCrawlerSource(follow_homepage_links=False)
            results = await src.fetch("example.com")

        assert results == []

    @pytest.mark.asyncio
    async def test_contact_page_gets_correct_source_type(self) -> None:
        homepage_html = ""
        contact_html = "Reach us: contact@example.com"

        call_count = 0

        async def _get(url: str, **kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _mock_response(homepage_html)
            if "contact" in url:
                return _mock_response(contact_html)
            return _mock_response("", status_code=404)

        with patch("coldreach.sources.web_crawler.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = _get
            mock_client_cls.return_value = mock_client

            src = WebCrawlerSource(follow_homepage_links=False)
            results = await src.fetch("example.com")

        contact_results = [r for r in results if r.source == EmailSource.WEBSITE_CONTACT]
        assert any(r.email == "contact@example.com" for r in contact_results)

    @pytest.mark.asyncio
    async def test_deduplicates_across_pages(self) -> None:
        html = "hello@example.com"

        with patch("coldreach.sources.web_crawler.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=_mock_response(html))
            mock_client_cls.return_value = mock_client

            src = WebCrawlerSource(follow_homepage_links=False)
            results = await src.fetch("example.com")

        emails = [r.email for r in results]
        assert emails.count("hello@example.com") == 1

    @pytest.mark.asyncio
    async def test_source_name_is_web_crawler(self) -> None:
        src = WebCrawlerSource()
        assert src.name == "web_crawler"
