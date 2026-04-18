"""
Unit tests for coldreach.verify.holehe

holehe HTTP calls are mocked — no real network traffic.
"""

from __future__ import annotations

import importlib.util
from unittest.mock import MagicMock, patch

import pytest

from coldreach.verify._types import CheckStatus
from coldreach.verify.holehe import check_holehe

# Tests that patch holehe.core require the module to be importable.
# Skip them when holehe is not installed (it's an optional extra: pip install coldreach[full]).
_holehe_installed = importlib.util.find_spec("holehe") is not None
requires_holehe = pytest.mark.skipif(
    not _holehe_installed, reason="holehe not installed (pip install coldreach[full])"
)


def _make_modules(results: list[dict]) -> list:
    """Build fake holehe module coroutine functions that append *results* to out."""
    modules = []
    for r in results:
        captured = r

        async def _mod(_email, _client, out, _r=captured):
            out.append(_r)

        modules.append(_mod)
    return modules


def _patch_holehe_core(modules):
    """Patch holehe.core so check_holehe uses our fake modules."""
    return patch.multiple(
        "holehe.core",
        import_submodules=MagicMock(return_value=MagicMock()),
        get_functions=MagicMock(return_value=modules),
    )


class TestCheckHolehe:
    @pytest.mark.asyncio
    async def test_skips_when_holehe_not_installed(self) -> None:
        import sys

        with patch.dict(sys.modules, {"holehe": None, "holehe.core": None}):
            result = await check_holehe("test@example.com")
        assert result.status == CheckStatus.SKIP

    @requires_holehe
    @pytest.mark.asyncio
    async def test_returns_pass_with_high_score_for_two_platforms(self) -> None:
        mods = _make_modules(
            [
                {"name": "github", "domain": "github.com", "exists": True},
                {"name": "discord", "domain": "discord.com", "exists": True},
            ]
        )
        with _patch_holehe_core(mods):
            result = await check_holehe("test@example.com")
        assert result.passed
        assert result.score_delta == 15
        assert result.metadata["platform_count"] == 2

    @requires_holehe
    @pytest.mark.asyncio
    async def test_returns_pass_with_low_score_for_one_platform(self) -> None:
        mods = _make_modules(
            [
                {"name": "github", "domain": "github.com", "exists": True},
                {"name": "discord", "domain": "discord.com", "exists": False},
            ]
        )
        with _patch_holehe_core(mods):
            result = await check_holehe("test@example.com")
        assert result.passed
        assert result.score_delta == 5
        assert result.metadata["platform_count"] == 1

    @requires_holehe
    @pytest.mark.asyncio
    async def test_returns_warn_for_zero_platforms(self) -> None:
        mods = _make_modules(
            [
                {"name": "github", "domain": "github.com", "exists": False},
            ]
        )
        with _patch_holehe_core(mods):
            result = await check_holehe("test@example.com")
        assert result.status == CheckStatus.WARN
        assert result.score_delta == 0
        assert result.metadata["platform_count"] == 0

    @requires_holehe
    @pytest.mark.asyncio
    async def test_handles_module_exception_gracefully(self) -> None:
        async def _bad_module(_email, _client, _out):
            raise RuntimeError("network error")

        with _patch_holehe_core([_bad_module]):
            result = await check_holehe("test@example.com")
        # Exception is caught; 0 platforms → WARN
        assert result.status == CheckStatus.WARN

    @requires_holehe
    @pytest.mark.asyncio
    async def test_custom_min_platforms_threshold(self) -> None:
        # 3 found, but min_platforms=4 → only +5
        mods = _make_modules(
            [
                {"name": "github", "exists": True},
                {"name": "discord", "exists": True},
                {"name": "spotify", "exists": True},
            ]
        )
        with _patch_holehe_core(mods):
            result = await check_holehe("test@example.com", min_platforms=4)
        assert result.score_delta == 5

    @requires_holehe
    @pytest.mark.asyncio
    async def test_platform_names_in_metadata(self) -> None:
        mods = _make_modules(
            [
                {"name": "github", "domain": "github.com", "exists": True},
                {"name": "spotify", "domain": "spotify.com", "exists": True},
            ]
        )
        with _patch_holehe_core(mods):
            result = await check_holehe("test@example.com")
        assert "github" in result.metadata["platforms"]
        assert "spotify" in result.metadata["platforms"]

    @requires_holehe
    @pytest.mark.asyncio
    async def test_no_modules_returns_warn(self) -> None:
        with _patch_holehe_core([]):
            result = await check_holehe("test@example.com")
        assert result.status == CheckStatus.WARN
