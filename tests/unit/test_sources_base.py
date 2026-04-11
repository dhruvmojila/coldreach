"""
Unit tests for coldreach.sources.base
"""

from __future__ import annotations

import pytest

from coldreach.core.models import EmailSource
from coldreach.sources.base import BaseSource, SourceResult, SourceSummary

# ---------------------------------------------------------------------------
# Concrete stub for testing ABC
# ---------------------------------------------------------------------------


class _OkSource(BaseSource):
    name = "ok_source"

    async def fetch(self, domain: str, *, person_name: str | None = None) -> list[SourceResult]:
        return [
            SourceResult(
                email=f"hello@{domain}",
                source=EmailSource.WEBSITE_CONTACT,
                url=f"https://{domain}/contact",
                context="stub",
                confidence_hint=35,
            )
        ]


class _ErrorSource(BaseSource):
    name = "error_source"

    async def fetch(self, domain: str, *, person_name: str | None = None) -> list[SourceResult]:
        raise RuntimeError("boom")


class _EmptySource(BaseSource):
    name = "empty_source"

    async def fetch(self, domain: str, *, person_name: str | None = None) -> list[SourceResult]:
        return []


# ---------------------------------------------------------------------------
# SourceResult
# ---------------------------------------------------------------------------


class TestSourceResult:
    def test_defaults(self) -> None:
        r = SourceResult(email="a@b.com", source=EmailSource.WHOIS)
        assert r.url == ""
        assert r.context == ""
        assert r.confidence_hint == 0

    def test_fields_stored(self) -> None:
        r = SourceResult(
            email="x@y.com",
            source=EmailSource.GITHUB_COMMIT,
            url="https://github.com/org/repo/commit/abc",
            context="commit by dev",
            confidence_hint=25,
        )
        assert r.email == "x@y.com"
        assert r.source == EmailSource.GITHUB_COMMIT
        assert r.confidence_hint == 25


# ---------------------------------------------------------------------------
# SourceSummary
# ---------------------------------------------------------------------------


class TestSourceSummary:
    def test_defaults(self) -> None:
        s = SourceSummary(source_name="test")
        assert s.found == 0
        assert s.errors == []
        assert s.skipped is False

    def test_fields(self) -> None:
        s = SourceSummary(source_name="web", found=3)
        assert s.found == 3


# ---------------------------------------------------------------------------
# BaseSource.run — safe wrapper
# ---------------------------------------------------------------------------


class TestBaseSourceRun:
    @pytest.mark.asyncio
    async def test_run_returns_results_on_success(self) -> None:
        src = _OkSource()
        results, summary = await src.run("example.com")
        assert len(results) == 1
        assert results[0].email == "hello@example.com"
        assert summary.found == 1
        assert summary.errors == []

    @pytest.mark.asyncio
    async def test_run_returns_empty_on_exception(self) -> None:
        src = _ErrorSource()
        results, summary = await src.run("example.com")
        assert results == []
        assert len(summary.errors) == 1
        assert "boom" in summary.errors[0]

    @pytest.mark.asyncio
    async def test_run_empty_source_gives_zero_found(self) -> None:
        src = _EmptySource()
        results, summary = await src.run("example.com")
        assert results == []
        assert summary.found == 0

    @pytest.mark.asyncio
    async def test_run_passes_person_name(self) -> None:
        class _NameCapture(BaseSource):
            name = "capture"
            captured: str | None = None

            async def fetch(
                self, domain: str, *, person_name: str | None = None
            ) -> list[SourceResult]:
                _NameCapture.captured = person_name
                return []

        src = _NameCapture()
        await src.run("example.com", person_name="Jane Doe")
        assert _NameCapture.captured == "Jane Doe"

    @pytest.mark.asyncio
    async def test_run_summary_has_correct_source_name(self) -> None:
        src = _OkSource()
        _, summary = await src.run("example.com")
        assert summary.source_name == "ok_source"
