"""
Unit tests for coldreach.verify.reacher

Reacher HTTP calls are mocked — no real SMTP traffic.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from coldreach.verify._types import CheckStatus
from coldreach.verify.reacher import _parse_reacher_response, check_reacher

# ---------------------------------------------------------------------------
# _parse_reacher_response (pure, no network)
# ---------------------------------------------------------------------------


def _reacher_data(
    *,
    can_connect: bool = True,
    is_deliverable: bool = True,
    is_catch_all: bool = False,
    has_full_inbox: bool = False,
    is_disabled: bool = False,
    mx_records: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "smtp": {
            "can_connect_smtp": can_connect,
            "is_deliverable": is_deliverable,
            "is_catch_all": is_catch_all,
            "has_full_inbox": has_full_inbox,
            "is_disabled": is_disabled,
        },
        "mx": {
            "accepts_mail": True,
            "records": mx_records or [],
        },
    }


class TestParseReacherResponse:
    def test_deliverable_returns_pass(self) -> None:
        result = _parse_reacher_response("x@example.com", _reacher_data())
        assert result.passed
        assert result.score_delta == 20

    def test_deliverable_sets_smtp_metadata(self) -> None:
        result = _parse_reacher_response("x@example.com", _reacher_data())
        assert result.metadata.get("smtp_deliverable") is True

    def test_cannot_connect_returns_fail(self) -> None:
        result = _parse_reacher_response("x@example.com", _reacher_data(can_connect=False))
        assert result.failed
        assert result.score_delta == -20

    def test_smtp_rejected_returns_fail(self) -> None:
        result = _parse_reacher_response("x@example.com", _reacher_data(is_deliverable=False))
        assert result.failed

    def test_disabled_mailbox_returns_fail(self) -> None:
        result = _parse_reacher_response("x@example.com", _reacher_data(is_disabled=True))
        assert result.failed

    def test_catch_all_returns_warn(self) -> None:
        result = _parse_reacher_response("x@example.com", _reacher_data(is_catch_all=True))
        assert result.status == CheckStatus.WARN
        assert result.metadata.get("is_catch_all") is True

    def test_full_inbox_returns_warn(self) -> None:
        result = _parse_reacher_response("x@example.com", _reacher_data(has_full_inbox=True))
        assert result.status == CheckStatus.WARN

    def test_positive_score_on_pass(self) -> None:
        result = _parse_reacher_response("x@example.com", _reacher_data())
        assert result.score_delta > 0

    def test_negative_score_on_fail(self) -> None:
        result = _parse_reacher_response("x@example.com", _reacher_data(can_connect=False))
        assert result.score_delta < 0


# ---------------------------------------------------------------------------
# check_reacher (mocked HTTP)
# ---------------------------------------------------------------------------


def _mock_http_response(data: dict[str, object], status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.json = MagicMock(return_value=data)
    return resp


class TestCheckReacher:
    @pytest.mark.asyncio
    async def test_returns_pass_for_deliverable(self) -> None:
        resp = _mock_http_response(_reacher_data())

        with patch("coldreach.verify.reacher.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=resp)
            mock_cls.return_value = mock_client

            result = await check_reacher("x@example.com", reacher_url="http://localhost:8083")

        assert result.passed

    @pytest.mark.asyncio
    async def test_returns_skip_on_connect_error(self) -> None:
        import httpx

        with patch("coldreach.verify.reacher.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
            mock_cls.return_value = mock_client

            result = await check_reacher("x@example.com", reacher_url="http://localhost:8083")

        assert result.status == CheckStatus.SKIP

    @pytest.mark.asyncio
    async def test_returns_skip_on_non_200(self) -> None:
        resp = _mock_http_response({}, status=503)

        with patch("coldreach.verify.reacher.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=resp)
            mock_cls.return_value = mock_client

            result = await check_reacher("x@example.com", reacher_url="http://localhost:8083")

        assert result.status == CheckStatus.SKIP

    @pytest.mark.asyncio
    async def test_invalid_email_returns_fail(self) -> None:
        result = await check_reacher("notanemail", reacher_url="http://localhost:8083")
        assert result.failed

    @pytest.mark.asyncio
    async def test_catch_all_returns_warn(self) -> None:
        resp = _mock_http_response(_reacher_data(is_catch_all=True))

        with patch("coldreach.verify.reacher.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=resp)
            mock_cls.return_value = mock_client

            result = await check_reacher("x@example.com", reacher_url="http://localhost:8083")

        assert result.status == CheckStatus.WARN
