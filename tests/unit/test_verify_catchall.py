"""
Unit tests for coldreach.verify.catchall
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from coldreach.verify._types import CheckStatus
from coldreach.verify.catchall import check_catchall, clear_cache, is_catch_all


@pytest.fixture(autouse=True)
def _clear_catchall_cache() -> None:
    """Reset module-level cache before each test."""
    clear_cache()


class TestCheckCatchall:
    @pytest.mark.asyncio
    async def test_skip_when_no_reacher_url(self) -> None:
        result = await check_catchall("example.com", reacher_url=None)
        assert result.status == CheckStatus.SKIP

    @pytest.mark.asyncio
    async def test_fail_when_probe_is_deliverable(self) -> None:
        with patch(
            "coldreach.verify.catchall._probe_via_reacher",
            new_callable=AsyncMock,
            return_value=True,
        ):
            result = await check_catchall("example.com", reacher_url="http://localhost:8083")

        assert result.failed
        assert result.score_delta == -40
        assert result.metadata.get("is_catch_all") is True

    @pytest.mark.asyncio
    async def test_pass_when_probe_not_deliverable(self) -> None:
        with patch(
            "coldreach.verify.catchall._probe_via_reacher",
            new_callable=AsyncMock,
            return_value=False,
        ):
            result = await check_catchall("example.com", reacher_url="http://localhost:8083")

        assert result.passed

    @pytest.mark.asyncio
    async def test_skip_when_probe_inconclusive(self) -> None:
        with patch(
            "coldreach.verify.catchall._probe_via_reacher",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await check_catchall("example.com", reacher_url="http://localhost:8083")

        assert result.status == CheckStatus.SKIP

    @pytest.mark.asyncio
    async def test_caches_result_on_second_call(self) -> None:
        call_count = 0

        async def _probe(*args: object, **kwargs: object) -> bool:
            nonlocal call_count
            call_count += 1
            return False

        with patch("coldreach.verify.catchall._probe_via_reacher", side_effect=_probe):
            await check_catchall("example.com", reacher_url="http://localhost:8083")
            await check_catchall("example.com", reacher_url="http://localhost:8083")

        assert call_count == 1  # second call used cache

    @pytest.mark.asyncio
    async def test_empty_domain_returns_fail(self) -> None:
        result = await check_catchall("", reacher_url="http://localhost:8083")
        assert result.failed


class TestIsCatchAll:
    @pytest.mark.asyncio
    async def test_returns_false_when_not_catch_all(self) -> None:
        with patch(
            "coldreach.verify.catchall._probe_via_reacher",
            new_callable=AsyncMock,
            return_value=False,
        ):
            result = await is_catch_all("example.com", reacher_url="http://localhost:8083")

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_true_when_catch_all(self) -> None:
        with patch(
            "coldreach.verify.catchall._probe_via_reacher",
            new_callable=AsyncMock,
            return_value=True,
        ):
            result = await is_catch_all("example.com", reacher_url="http://localhost:8083")

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_none_when_no_reacher(self) -> None:
        result = await is_catch_all("example.com", reacher_url=None)
        assert result is None
