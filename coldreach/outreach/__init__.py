"""
ColdReach outreach module.

Provides:
  get_company_context(domain)   → CompanyContext
  draft_email(...)              → EmailDraft
  TEMPLATES                     → dict of built-in ColdEmailTemplate objects
  EmailType                     → StrEnum of email types
"""

from coldreach.outreach.context import CompanyContext, get_company_context
from coldreach.outreach.draft import EmailDraft, draft_email
from coldreach.outreach.templates import TEMPLATES, ColdEmailTemplate, EmailType

__all__ = [
    "TEMPLATES",
    "ColdEmailTemplate",
    "CompanyContext",
    "EmailDraft",
    "EmailType",
    "draft_email",
    "get_company_context",
]
