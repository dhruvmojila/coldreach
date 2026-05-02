"""
Unit tests for coldreach.sources.github

All HTTP calls are mocked.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from coldreach.core.models import EmailSource
from coldreach.sources.github import GitHubSource, _domain_to_slug, _is_noreply

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_commit(email: str, name: str = "Dev", repo: str = "org/repo") -> dict[str, Any]:
    return {
        "commit": {"author": {"email": email, "name": name}},
        "html_url": f"https://github.com/{repo}/commit/abc123",
    }


def _mock_json_response(data: Any, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json = MagicMock(return_value=data)
    return resp


# ---------------------------------------------------------------------------
# _domain_to_slug
# ---------------------------------------------------------------------------


class TestDomainToSlug:
    def test_simple_com(self) -> None:
        assert _domain_to_slug("stripe.com") == "stripe"

    def test_io_domain(self) -> None:
        assert _domain_to_slug("vercel.io") == "vercel"

    def test_co_uk(self) -> None:
        assert _domain_to_slug("acme.co.uk") == "acme"

    def test_hyphenated(self) -> None:
        assert _domain_to_slug("my-company.com") == "my-company"


# ---------------------------------------------------------------------------
# _is_noreply
# ---------------------------------------------------------------------------


class TestIsNoreply:
    def test_noreply_github(self) -> None:
        assert _is_noreply("123+user@users.noreply.github.com") is True

    def test_noreply_word(self) -> None:
        assert _is_noreply("noreply@example.com") is True

    def test_real_email(self) -> None:
        assert _is_noreply("dev@example.com") is False


# ---------------------------------------------------------------------------
# GitHubSource.fetch
# ---------------------------------------------------------------------------


class TestGitHubSourceFetch:
    @pytest.mark.asyncio
    async def test_finds_domain_email_in_commits(self) -> None:
        repos = [{"full_name": "stripe/stripe-python"}]
        commits = [_make_commit("dev@stripe.com", repo="stripe/stripe-python")]

        with patch("coldreach.sources.github.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)

            mock_client.get = AsyncMock(
                side_effect=[
                    _mock_json_response(repos),  # org repos
                    _mock_json_response(commits),  # commits
                ]
            )
            mock_cls.return_value = mock_client

            src = GitHubSource()
            results = await src.fetch("stripe.com")

        assert len(results) == 1
        assert results[0].email == "dev@stripe.com"
        assert results[0].source == EmailSource.GITHUB_COMMIT

    @pytest.mark.asyncio
    async def test_filters_out_noreply_emails(self) -> None:
        repos = [{"full_name": "acme/repo"}]
        commits = [_make_commit("123+user@users.noreply.github.com")]

        with patch("coldreach.sources.github.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(
                side_effect=[
                    _mock_json_response(repos),
                    _mock_json_response(commits),
                ]
            )
            mock_cls.return_value = mock_client

            src = GitHubSource()
            results = await src.fetch("acme.com")

        assert results == []

    @pytest.mark.asyncio
    async def test_filters_emails_from_other_domains(self) -> None:
        repos = [{"full_name": "acme/repo"}]
        commits = [_make_commit("personal@gmail.com")]

        with patch("coldreach.sources.github.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(
                side_effect=[
                    _mock_json_response(repos),
                    _mock_json_response(commits),
                ]
            )
            mock_cls.return_value = mock_client

            src = GitHubSource()
            results = await src.fetch("acme.com")

        assert results == []

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_repos_found(self) -> None:
        with patch("coldreach.sources.github.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            # We try up to 7 slug variants x 2 endpoints = up to 14 requests.
            # Return 404 for all of them.
            mock_client.get = AsyncMock(return_value=_mock_json_response({}, status_code=404))
            mock_cls.return_value = mock_client

            src = GitHubSource()
            results = await src.fetch("unknown-company.com")

        assert results == []

    @pytest.mark.asyncio
    async def test_deduplicates_same_email_across_commits(self) -> None:
        repos = [{"full_name": "acme/repo"}]
        commits = [
            _make_commit("dev@acme.com"),
            _make_commit("dev@acme.com"),  # duplicate
        ]

        with patch("coldreach.sources.github.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(
                side_effect=[
                    _mock_json_response(repos),
                    _mock_json_response(commits),
                ]
            )
            mock_cls.return_value = mock_client

            src = GitHubSource()
            results = await src.fetch("acme.com")

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_source_name(self) -> None:
        assert GitHubSource().name == "github"
