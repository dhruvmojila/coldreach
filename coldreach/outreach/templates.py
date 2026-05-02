"""
Built-in cold email templates and user-saved template management.

Templates guide the DSPy signature with intent hints and tone guidelines.
Users can save custom templates to ~/.coldreach/templates.json.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

_TEMPLATES_PATH = Path("~/.coldreach/templates.json").expanduser()


class EmailType(StrEnum):
    JOB_APPLICATION = "job_application"
    PARTNERSHIP = "partnership"
    SALES = "sales"
    INTRODUCTION = "introduction"
    CUSTOM = "custom"


@dataclass
class ColdEmailTemplate:
    """A reusable cold email template with intent and tone guidance."""

    name: str
    email_type: EmailType
    intent_hint: str  # sentence that goes into the DSPy prompt
    tone: str  # "professional", "casual", "direct"
    subject_hint: str  # hint for Groq on subject style
    length_guidance: str  # "2-3 sentences", "4-5 sentences"
    do_not_include: list[str] = field(default_factory=list)  # phrases to avoid

    def to_prompt_guidance(self) -> str:
        """Return a concise guidance string for the DSPy prompt."""
        lines = [
            f"Intent: {self.intent_hint}",
            f"Tone: {self.tone}",
            f"Subject style: {self.subject_hint}",
            f"Body length: {self.length_guidance}",
        ]
        if self.do_not_include:
            lines.append(f"Avoid: {', '.join(self.do_not_include)}")
        return "\n".join(lines)


# Built-in templates
TEMPLATES: dict[EmailType, ColdEmailTemplate] = {
    EmailType.JOB_APPLICATION: ColdEmailTemplate(
        name="Job Application",
        email_type=EmailType.JOB_APPLICATION,
        intent_hint="I'm interested in joining your team and want to learn about opportunities",
        tone="professional and enthusiastic",
        subject_hint="Specific role or skill, under 8 words",
        length_guidance="3-4 sentences: introduce yourself, mention specific value, ask for 15 min",
        do_not_include=["I am reaching out", "I hope this email finds you", "per my last email"],
    ),
    EmailType.PARTNERSHIP: ColdEmailTemplate(
        name="Partnership Proposal",
        email_type=EmailType.PARTNERSHIP,
        intent_hint="I see a mutual benefit and want to explore a business partnership",
        tone="direct and value-first",
        subject_hint="Mention specific shared angle or outcome",
        length_guidance="3 sentences — shared context, specific value, clear ask",
        do_not_include=["synergy", "leverage", "circle back", "low-hanging fruit"],
    ),
    EmailType.SALES: ColdEmailTemplate(
        name="Sales Outreach",
        email_type=EmailType.SALES,
        intent_hint="I have a product or service that solves a specific problem they have",
        tone="casual and specific, not salesy",
        subject_hint="Reference something specific about their company",
        length_guidance="2-3 sentences — specific problem, specific solution, low-friction CTA",
        do_not_include=["I noticed you", "just checking in", "touching base", "quick question"],
    ),
    EmailType.INTRODUCTION: ColdEmailTemplate(
        name="Introduction",
        email_type=EmailType.INTRODUCTION,
        intent_hint="I want to connect and build a relationship without a specific ask",
        tone="warm and genuine",
        subject_hint="Mention common ground or specific admiration",
        length_guidance="2-3 sentences — genuine compliment, who you are, open-ended question",
        do_not_include=["I'm a huge fan", "I love your work", "I was wondering"],
    ),
}


def get_template(email_type: EmailType) -> ColdEmailTemplate:
    """Return the built-in template for *email_type*, falling back to INTRODUCTION."""
    return TEMPLATES.get(email_type, TEMPLATES[EmailType.INTRODUCTION])


def auto_detect_type(intent: str) -> EmailType:
    """Guess email type from the user's intent sentence."""
    intent_lower = intent.lower()
    if any(w in intent_lower for w in ["job", "role", "position", "hire", "apply", "work at"]):
        return EmailType.JOB_APPLICATION
    if any(w in intent_lower for w in ["partner", "collaboration", "integrate", "joint"]):
        return EmailType.PARTNERSHIP
    if any(w in intent_lower for w in ["sell", "demo", "product", "service", "solution", "offer"]):
        return EmailType.SALES
    return EmailType.INTRODUCTION


# User-saved custom templates
def load_user_templates() -> dict[str, ColdEmailTemplate]:
    """Load user-saved templates from ~/.coldreach/templates.json."""
    if not _TEMPLATES_PATH.exists():
        return {}
    try:
        data = json.loads(_TEMPLATES_PATH.read_text())
        result = {}
        for key, val in data.items():
            result[key] = ColdEmailTemplate(
                name=val["name"],
                email_type=EmailType(val.get("email_type", "custom")),
                intent_hint=val.get("intent_hint", ""),
                tone=val.get("tone", "professional"),
                subject_hint=val.get("subject_hint", ""),
                length_guidance=val.get("length_guidance", "3-4 sentences"),
                do_not_include=val.get("do_not_include", []),
            )
        return result
    except Exception:
        return {}


def save_user_template(key: str, template: ColdEmailTemplate) -> None:
    """Save a custom template to ~/.coldreach/templates.json."""
    _TEMPLATES_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, object] = {}
    if _TEMPLATES_PATH.exists():
        import contextlib

        with contextlib.suppress(Exception):
            existing = json.loads(_TEMPLATES_PATH.read_text())
    existing[key] = {
        "name": template.name,
        "email_type": template.email_type.value,
        "intent_hint": template.intent_hint,
        "tone": template.tone,
        "subject_hint": template.subject_hint,
        "length_guidance": template.length_guidance,
        "do_not_include": template.do_not_include,
    }
    _TEMPLATES_PATH.write_text(json.dumps(existing, indent=2))
