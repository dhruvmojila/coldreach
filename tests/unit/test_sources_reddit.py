"""
Unit tests for coldreach.sources.reddit

All HTTP calls are mocked.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from coldreach.core.models import EmailSource
from coldreach.sources.reddit import RedditSource, _extract_domain_emails

# ---------------------------------------------------------------------------
# _extract_domain_emails
# ---------------------------------------------------------------------------


class TestExtractDomainEmails:
    def test_finds_matching_email(self) -> None:
        text = "Contact us at hello@example.com for support"
        assert "hello@example.com" in _extract_domain_emails(text, "example.com")

    def test_ignores_other_domains(self) -> None:
        text = "hello@other.com and contact@example.com"
        result = _extract_domain_emails(text, "example.com")
        assert "contact@example.com" in result
        assert "hello@other.com" not in result

    def test_deduplicates(self) -> None:
        text = "hello@example.com hello@example.com"
        result = _extract_domain_emails(text, "example.com")
        assert result.count("hello@example.com") == 1

    def test_normalises_to_lowercase(self) -> None:
        text = "Hello@Example.COM"
        result = _extract_domain_emails(text, "example.com")
        assert "hello@example.com" in result

    def test_empty_text(self) -> None:
        assert _extract_domain_emails("", "example.com") == []


# ---------------------------------------------------------------------------
# RedditSource.fetch
# ---------------------------------------------------------------------------


def _reddit_response(posts: list[dict[str, Any]], status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    children = [{"data": p} for p in posts]
    resp.json = MagicMock(return_value={"data": {"children": children}})
    return resp


class TestRedditSourceFetch:
    @pytest.mark.asyncio
    async def test_finds_email_in_post_selftext(self) -> None:
        posts = [
            {
                "title": "Acme company contact",
                "selftext": "reach them at hello@acme.com",
                "url": "https://reddit.com/r/test/comments/1",
            }
        ]

        with patch("coldreach.sources.reddit.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=_reddit_response(posts))
            mock_cls.return_value = mock_client

            src = RedditSource()
            results = await src.fetch("acme.com")

        assert any(r.email == "hello@acme.com" for r in results)
        assert all(r.source == EmailSource.REDDIT for r in results)

    @pytest.mark.asyncio
    async def test_ignores_emails_from_other_domains(self) -> None:
        posts = [
            {
                "title": "test",
                "selftext": "contact@gmail.com",
                "url": "https://reddit.com/r/test/comments/2",
            }
        ]

        with patch("coldreach.sources.reddit.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=_reddit_response(posts))
            mock_cls.return_value = mock_client

            src = RedditSource()
            results = await src.fetch("acme.com")

        assert results == []

    @pytest.mark.asyncio
    async def test_returns_empty_on_http_error(self) -> None:
        with patch("coldreach.sources.reddit.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=_reddit_response([], status_code=429))
            mock_cls.return_value = mock_client

            src = RedditSource()
            results = await src.fetch("acme.com")

        assert results == []

    @pytest.mark.asyncio
    async def test_deduplicates_across_posts(self) -> None:
        posts = [
            {"title": "post1", "selftext": "hello@acme.com", "url": "https://reddit.com/1"},
            {"title": "post2", "selftext": "hello@acme.com", "url": "https://reddit.com/2"},
        ]

        with patch("coldreach.sources.reddit.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=_reddit_response(posts))
            mock_cls.return_value = mock_client

            src = RedditSource()
            results = await src.fetch("acme.com")

        emails = [r.email for r in results]
        assert emails.count("hello@acme.com") == 1

    @pytest.mark.asyncio
    async def test_source_name(self) -> None:
        assert RedditSource().name == "reddit"
