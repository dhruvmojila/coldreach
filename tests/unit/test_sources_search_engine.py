"""
Unit tests for coldreach.sources.search_engine

All HTTP calls are mocked.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from coldreach.core.models import EmailSource
from coldreach.sources.search_engine import (
    SearchEngineSource,
    _build_queries,
    _extract_domain_emails,
)


class TestExtractDomainEmails:
    def test_finds_matching_email(self) -> None:
        text = "contact hello@example.com for details"
        result = _extract_domain_emails(text, "example.com")
        assert "hello@example.com" in result

    def test_ignores_other_domains(self) -> None:
        result = _extract_domain_emails("a@other.com b@example.com", "example.com")
        assert "b@example.com" in result
        assert "a@other.com" not in result

    def test_deduplicates(self) -> None:
        text = "a@example.com a@example.com"
        assert _extract_domain_emails(text, "example.com").count("a@example.com") == 1

    def test_empty_text(self) -> None:
        assert _extract_domain_emails("", "example.com") == []


class TestBuildQueries:
    def test_always_includes_at_query(self) -> None:
        queries = _build_queries("example.com", None)
        assert any("@example.com" in q for q in queries)

    def test_includes_person_query_when_given(self) -> None:
        queries = _build_queries("example.com", "John Smith")
        assert any("John Smith" in q for q in queries)

    def test_no_person_no_name_query(self) -> None:
        queries = _build_queries("example.com", None)
        assert all("John Smith" not in q for q in queries)


class TestSearchEngineSource:
    def _make_searxng_response(self, emails: list[str], domain: str) -> MagicMock:
        resp = MagicMock()
        resp.status_code = 200
        content = " ".join(emails)
        resp.json = MagicMock(
            return_value={"results": [{"content": content, "title": "", "url": ""}]}
        )
        return resp

    @pytest.mark.asyncio
    async def test_finds_email_via_searxng(self) -> None:
        with patch("coldreach.sources.search_engine.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(
                return_value=self._make_searxng_response(["hello@example.com"], "example.com")
            )
            mock_client.post = AsyncMock(return_value=MagicMock(status_code=404))
            mock_cls.return_value = mock_client

            src = SearchEngineSource(
                searxng_url="http://localhost:8080",
                query_delay=0.0,
            )
            results = await src.fetch("example.com")

        assert any(r.email == "hello@example.com" for r in results)
        assert all(r.source == EmailSource.SEARXNG for r in results)

    @pytest.mark.asyncio
    async def test_returns_empty_when_all_backends_fail(self) -> None:
        with patch("coldreach.sources.search_engine.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=MagicMock(status_code=503))
            mock_client.post = AsyncMock(return_value=MagicMock(status_code=503))
            mock_cls.return_value = mock_client

            src = SearchEngineSource(
                searxng_url="http://localhost:8080",
                query_delay=0.0,
            )
            results = await src.fetch("example.com")

        assert results == []

    @pytest.mark.asyncio
    async def test_deduplicates_across_queries(self) -> None:
        # Same email returned by every query
        with patch("coldreach.sources.search_engine.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(
                return_value=self._make_searxng_response(["hello@example.com"], "example.com")
            )
            mock_cls.return_value = mock_client

            src = SearchEngineSource(
                searxng_url="http://localhost:8080",
                query_delay=0.0,
            )
            results = await src.fetch("example.com")

        emails = [r.email for r in results]
        assert emails.count("hello@example.com") == 1

    @pytest.mark.asyncio
    async def test_skips_searxng_when_url_is_none(self) -> None:
        with patch("coldreach.sources.search_engine._query_ddg_lite") as mock_ddg:
            mock_ddg.return_value = []
            src = SearchEngineSource(searxng_url=None, query_delay=0.0)

            with patch("coldreach.sources.search_engine.httpx.AsyncClient") as mock_cls:
                mock_client = AsyncMock()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                mock_cls.return_value = mock_client

                await src.fetch("example.com")

        # DDG should be tried since SearXNG was skipped
        assert mock_ddg.called

    def test_source_name(self) -> None:
        assert SearchEngineSource().name == "search_engine"
