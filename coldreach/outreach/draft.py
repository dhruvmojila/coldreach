"""
Groq-powered cold email drafting via DSPy.

Uses DSPy's typed Predict for structured output (subject + body as
separate fields).  This means no regex parsing of LLM output and the
prompt is tunable via BootstrapFewShot if output quality needs improving.

Usage:
    from coldreach.outreach.draft import draft_email, EmailType

    context = await get_company_context("stripe.com")
    draft = await draft_email(
        email="patrick@stripe.com",
        context=context,
        sender_name="Jane Smith",
        sender_intent="explore a partnership on embedded payments",
    )
    print(draft.subject)
    print(draft.body)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Re-export EmailType so callers can import from draft module
from coldreach.outreach.context import CompanyContext  # noqa: E402
from coldreach.outreach.templates import EmailType, auto_detect_type, get_template  # noqa: E402


@dataclass
class EmailDraft:
    """A generated cold email draft."""

    to: str
    subject: str
    body: str
    email_type: EmailType
    tokens_used: int = 0
    model: str = "groq/llama-3.1-8b-instant"

    def formatted(self, sender_name: str = "") -> str:
        """Return a formatted email string ready to display or copy."""
        sig = f"\nBest,\n{sender_name}" if sender_name else ""
        return f"Subject: {self.subject}\n\n{self.body}{sig}"


def _get_drafter(api_key: str, model: str = "groq/llama-3.1-8b-instant") -> object:
    """Lazily configure DSPy and return a ColdEmail predictor.

    Configuration is per-call so different API keys / models can coexist.
    """
    import dspy  # lazy — DSPy is in [full] extras, not core deps

    class ColdEmailSignature(dspy.Signature):
        """Write a short, genuine, personalised cold email.
        Be specific about the company. No fluff. No fake enthusiasm.
        No 'I hope this email finds you well'. Maximum 4 sentences in the body."""

        company_context: str = dspy.InputField(
            desc="What the company does, their product, recent news, location"
        )
        recipient_email: str = dspy.InputField(desc="Email address of the recipient")
        sender_name: str = dspy.InputField(desc="Full name of the person sending this email")
        sender_intent: str = dspy.InputField(
            desc="One sentence: what the sender wants from this specific person"
        )
        template_guidance: str = dspy.InputField(desc="Tone, style, length and what to avoid")

        subject: str = dspy.OutputField(
            desc="Email subject line, under 60 characters, no clickbait, no ALL CAPS"
        )
        body: str = dspy.OutputField(
            desc="Plain text email body, 2-4 sentences max, no bullet points, no sign-off"
        )

    lm = dspy.LM(model, api_key=api_key, max_tokens=300)
    dspy.configure(lm=lm)
    return dspy.Predict(ColdEmailSignature)


async def draft_email(
    email: str,
    context: CompanyContext,
    sender_name: str,
    sender_intent: str,
    email_type: EmailType | None = None,
    *,
    api_key: str | None = None,
    model: str = "groq/llama-3.1-8b-instant",
) -> EmailDraft:
    """Generate a personalized cold email draft using Groq + DSPy.

    Parameters
    ----------
    email:
        Recipient email address.
    context:
        Company context from ``get_company_context()``.
    sender_name:
        The sender's full name (appears in sign-off and Groq context).
    sender_intent:
        One sentence describing what the sender wants.  This is the
        single most important input — be specific.
    email_type:
        Override the detected email type (job/partnership/sales/intro).
        Auto-detected from *sender_intent* if ``None``.
    api_key:
        Groq API key.  Falls back to ``COLDREACH_GROQ_API_KEY`` env var
        and then ``get_settings().groq_api_key``.
    model:
        Groq model identifier.  Default is the fastest free-tier model.

    Returns
    -------
    EmailDraft
        Structured draft with ``subject`` and ``body`` fields.
    """
    resolved_key = _resolve_api_key(api_key)
    if not resolved_key:
        raise ValueError(
            "Groq API key required for draft generation. "
            "Set COLDREACH_GROQ_API_KEY in .env or pass api_key= directly."
        )

    detected_type = email_type or auto_detect_type(sender_intent)
    template = get_template(detected_type)

    try:
        drafter = _get_drafter(resolved_key, model)
        # DSPy predictors are synchronous — run in thread to avoid blocking event loop
        result = await asyncio.to_thread(
            drafter,
            company_context=context.to_prompt_context(),
            recipient_email=email,
            sender_name=sender_name,
            sender_intent=sender_intent,
            template_guidance=template.to_prompt_guidance(),
        )
        subject = str(result.subject).strip()
        body = str(result.body).strip()

        # Sanity-check outputs — DSPy occasionally returns empty fields
        if not subject:
            subject = f"Quick question about {context.name}"
        if not body:
            raise ValueError("Groq returned empty body — retrying is recommended")

        logger.info("Draft generated for %s (%d chars body)", email, len(body))
        return EmailDraft(
            to=email,
            subject=subject,
            body=body,
            email_type=detected_type,
            model=model,
        )

    except Exception as exc:
        logger.warning("Draft generation failed: %s", exc)
        raise


def _resolve_api_key(explicit: str | None) -> str | None:
    """Return the first non-empty Groq API key found."""
    if explicit:
        return explicit
    import os

    env_key = os.getenv("COLDREACH_GROQ_API_KEY")
    if env_key:
        return env_key
    try:
        from coldreach.config import get_settings

        return get_settings().groq_api_key
    except Exception:
        return None
