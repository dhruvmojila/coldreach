"""
Unit tests for coldreach.outreach.draft

DSPy predictor is mocked — no real Groq API calls.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from coldreach.outreach.context import CompanyContext
from coldreach.outreach.draft import EmailDraft, EmailType, _resolve_api_key, draft_email
from coldreach.outreach.templates import auto_detect_type

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_context(domain: str = "stripe.com") -> CompanyContext:
    return CompanyContext(
        domain=domain,
        name="Stripe",
        description="Financial infrastructure for the internet.",
        industry="fintech",
        location="San Francisco, CA",
        recent_highlights="",
        raw_text="Payment APIs, fintech platform, global coverage.",
    )


def _mock_dspy_result(subject: str = "Quick question", body: str = "Hi there.") -> MagicMock:
    result = MagicMock()
    result.subject = subject
    result.body = body
    return result


# ---------------------------------------------------------------------------
# EmailType auto-detection
# ---------------------------------------------------------------------------


class TestAutoDetectType:
    def test_detects_job(self) -> None:
        assert auto_detect_type("I want to apply for a role") == EmailType.JOB_APPLICATION

    def test_detects_partnership(self) -> None:
        assert auto_detect_type("Explore a partnership opportunity") == EmailType.PARTNERSHIP

    def test_detects_sales(self) -> None:
        assert auto_detect_type("Demo our product to you") == EmailType.SALES

    def test_defaults_to_introduction(self) -> None:
        assert auto_detect_type("Just wanted to connect") == EmailType.INTRODUCTION


# ---------------------------------------------------------------------------
# _resolve_api_key
# ---------------------------------------------------------------------------


class TestResolveApiKey:
    def test_returns_explicit_key(self) -> None:
        assert _resolve_api_key("my-key") == "my-key"

    def test_falls_back_to_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("COLDREACH_GROQ_API_KEY", "env-key")
        assert _resolve_api_key(None) == "env-key"

    def test_returns_none_when_no_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("COLDREACH_GROQ_API_KEY", raising=False)
        # get_settings is a local import inside _resolve_api_key — patch at source
        with patch("coldreach.config.get_settings") as mock_settings_cls:
            mock_settings = mock_settings_cls.return_value
            mock_settings.groq_api_key = None
            result = _resolve_api_key(None)
        assert result is None


# ---------------------------------------------------------------------------
# draft_email
# ---------------------------------------------------------------------------


class TestDraftEmail:
    @pytest.mark.asyncio
    async def test_raises_without_api_key(self) -> None:
        with (
            patch("coldreach.outreach.draft._resolve_api_key", return_value=None),
            pytest.raises(ValueError, match="Groq API key required"),
        ):
            await draft_email(
                email="test@stripe.com",
                context=_make_context(),
                sender_name="Jane",
                sender_intent="explore partnership",
                api_key=None,
            )

    @pytest.mark.asyncio
    async def test_returns_email_draft(self) -> None:
        mock_result = _mock_dspy_result(
            subject="Quick question about Stripe's API",
            body="Hi Patrick, I came across Stripe's embedded finance work and wanted to connect.",
        )

        with (
            patch("coldreach.outreach.draft._resolve_api_key", return_value="test-key"),
            patch("coldreach.outreach.draft._get_drafter") as mock_drafter_fn,
        ):
            mock_predictor = MagicMock()
            mock_predictor.return_value = mock_result
            mock_drafter_fn.return_value = mock_predictor

            draft = await draft_email(
                email="patrick@stripe.com",
                context=_make_context(),
                sender_name="Jane Smith",
                sender_intent="explore a partnership on embedded payments",
            )

        assert isinstance(draft, EmailDraft)
        assert draft.to == "patrick@stripe.com"
        assert draft.subject == "Quick question about Stripe's API"
        assert "Patrick" in draft.body or "Hi" in draft.body
        assert draft.email_type == EmailType.PARTNERSHIP

    @pytest.mark.asyncio
    async def test_auto_detects_email_type(self) -> None:
        mock_result = _mock_dspy_result("Interview request", "Hi, I'm interested in the role.")

        with (
            patch("coldreach.outreach.draft._resolve_api_key", return_value="test-key"),
            patch("coldreach.outreach.draft._get_drafter") as mock_drafter_fn,
        ):
            mock_predictor = MagicMock()
            mock_predictor.return_value = mock_result
            mock_drafter_fn.return_value = mock_predictor

            draft = await draft_email(
                email="hr@stripe.com",
                context=_make_context(),
                sender_name="Jane",
                sender_intent="I want to apply for a software engineer role",
                email_type=None,
            )

        assert draft.email_type == EmailType.JOB_APPLICATION

    @pytest.mark.asyncio
    async def test_uses_explicit_email_type(self) -> None:
        mock_result = _mock_dspy_result("Sales pitch", "We solve payments.")

        with (
            patch("coldreach.outreach.draft._resolve_api_key", return_value="test-key"),
            patch("coldreach.outreach.draft._get_drafter") as mock_drafter_fn,
        ):
            mock_predictor = MagicMock()
            mock_predictor.return_value = mock_result
            mock_drafter_fn.return_value = mock_predictor

            draft = await draft_email(
                email="sales@stripe.com",
                context=_make_context(),
                sender_name="Bob",
                sender_intent="introduce our product",
                email_type=EmailType.SALES,
            )

        assert draft.email_type == EmailType.SALES

    @pytest.mark.asyncio
    async def test_falls_back_subject_when_empty(self) -> None:
        mock_result = _mock_dspy_result(subject="", body="Hi there!")

        with (
            patch("coldreach.outreach.draft._resolve_api_key", return_value="test-key"),
            patch("coldreach.outreach.draft._get_drafter") as mock_drafter_fn,
        ):
            mock_predictor = MagicMock()
            mock_predictor.return_value = mock_result
            mock_drafter_fn.return_value = mock_predictor

            draft = await draft_email(
                email="ceo@stripe.com",
                context=_make_context(),
                sender_name="Alice",
                sender_intent="say hello",
            )

        # Subject should fall back gracefully rather than being empty
        assert draft.subject  # non-empty

    @pytest.mark.asyncio
    async def test_raises_when_body_empty(self) -> None:
        mock_result = _mock_dspy_result(subject="Subject", body="")

        with (
            patch("coldreach.outreach.draft._resolve_api_key", return_value="test-key"),
            patch("coldreach.outreach.draft._get_drafter") as mock_drafter_fn,
        ):
            mock_predictor = MagicMock()
            mock_predictor.return_value = mock_result
            mock_drafter_fn.return_value = mock_predictor

            with pytest.raises(ValueError, match="empty body"):
                await draft_email(
                    email="ceo@stripe.com",
                    context=_make_context(),
                    sender_name="Alice",
                    sender_intent="say hello",
                )


# ---------------------------------------------------------------------------
# EmailDraft.formatted
# ---------------------------------------------------------------------------


class TestEmailDraftFormatted:
    def test_formats_with_sender(self) -> None:
        draft = EmailDraft(
            to="test@co.com",
            subject="Hello",
            body="Hi there.",
            email_type=EmailType.INTRODUCTION,
        )
        result = draft.formatted("Jane Smith")
        assert "Subject: Hello" in result
        assert "Hi there." in result
        assert "Jane Smith" in result

    def test_formats_without_sender(self) -> None:
        draft = EmailDraft(
            to="test@co.com",
            subject="Hello",
            body="Hi there.",
            email_type=EmailType.INTRODUCTION,
        )
        result = draft.formatted()
        assert "Subject: Hello" in result
        assert "Hi there." in result
