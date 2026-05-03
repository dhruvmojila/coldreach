"""
Reacher SMTP verification client.

Reacher (https://reacher.email) is a self-hosted Rust microservice that
performs full SMTP verification including:
  - SMTP connection test
  - RCPT TO probe (is the mailbox deliverable?)
  - Catch-all detection
  - MX record lookup (can be skipped if already known)

Requires the Reacher Docker service to be running:
  docker compose up reacher

API endpoint: POST /v0/check_email
Request:  { "to_email": "john@example.com" }
Response: Full JSON with smtp, mx, misc, syntax sections.

This checker is optional — gracefully returns SKIP if Reacher is
not running or not configured.
"""

from __future__ import annotations

import logging

import httpx

from coldreach.verify._types import CheckResult

logger = logging.getLogger(__name__)


async def check_reacher(
    email: str,
    *,
    reacher_url: str,
    timeout: float = 15.0,
) -> CheckResult:
    """Verify *email* via the Reacher SMTP microservice.

    Parameters
    ----------
    email:
        The email address to verify.
    reacher_url:
        Base URL of the Reacher service, e.g. ``"http://localhost:8083"``.
    timeout:
        HTTP timeout in seconds (SMTP handshakes can be slow).

    Returns
    -------
    CheckResult
        - PASS (+20): SMTP accepted, not catch-all
        - FAIL (-20): SMTP rejected or unreachable mailbox
        - WARN (0): deliverable but catch-all domain
        - SKIP: Reacher service unavailable
    """
    if not email or "@" not in email:
        return CheckResult.fail("Invalid email for Reacher check", score_delta=-10)

    url = f"{reacher_url.rstrip('/')}/v0/check_email"
    payload = {"to_email": email}

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload)
    except httpx.ConnectError:
        logger.debug("Reacher not reachable at %s — skipping SMTP check", reacher_url)
        return CheckResult.skip("Reacher service not running")
    except httpx.TimeoutException:
        logger.debug("Reacher timed out for %s", email)
        return CheckResult.skip("Reacher request timed out")
    except httpx.RequestError as exc:
        logger.debug("Reacher request error: %s", exc)
        return CheckResult.skip(f"Reacher request failed: {exc or 'connection error'}")

    if resp.status_code != 200:
        return CheckResult.skip(f"Reacher HTTP {resp.status_code}")

    try:
        data = resp.json()
    except Exception:
        return CheckResult.skip("Reacher returned invalid JSON")

    return _parse_reacher_response(email, data)


def _parse_reacher_response(email: str, data: dict[str, object]) -> CheckResult:
    """Interpret the Reacher JSON response into a CheckResult."""
    smtp = data.get("smtp") or {}
    if not isinstance(smtp, dict):
        return CheckResult.skip("Reacher response missing smtp section")

    is_catch_all: bool = bool(smtp.get("is_catch_all"))
    can_connect: bool = bool(smtp.get("can_connect_smtp"))
    is_deliverable: bool = bool(smtp.get("is_deliverable"))
    has_full_inbox: bool = bool(smtp.get("has_full_inbox"))
    is_disabled: bool = bool(smtp.get("is_disabled"))

    # MX records from response (bonus metadata)
    mx_section = data.get("mx") or {}
    if not isinstance(mx_section, dict):
        mx_section = {}
    mx_records: list[str] = []
    for entry in (mx_section.get("accepts_mail") and mx_section.get("records")) or []:
        if isinstance(entry, dict):
            host = str(entry.get("exchange", "")).rstrip(".")
            if host:
                mx_records.append(host)

    # Cannot connect to SMTP at all
    if not can_connect:
        return CheckResult.fail(
            "SMTP connection failed",
            score_delta=-20,
            smtp_can_connect=False,
        )

    # Mailbox explicitly rejected
    if is_disabled:
        return CheckResult.fail(
            "Mailbox is disabled",
            score_delta=-20,
            smtp_deliverable=False,
        )

    if has_full_inbox:
        # Technically exists but can't receive — risky
        return CheckResult.warn(
            "Mailbox full",
            score_delta=-5,
            smtp_deliverable=False,
        )

    # Catch-all: SMTP accepted but we can't trust it
    if is_catch_all:
        return CheckResult.warn(
            "Catch-all domain — SMTP result unreliable",
            score_delta=0,
            is_catch_all=True,
            mx_records=mx_records,
        )

    # Confirmed deliverable
    if is_deliverable:
        return CheckResult.pass_(
            score_delta=20,
            smtp_deliverable=True,
            is_catch_all=False,
            mx_records=mx_records,
        )

    # SMTP connected but RCPT TO not accepted
    return CheckResult.fail(
        "SMTP rejected RCPT TO",
        score_delta=-20,
        smtp_deliverable=False,
    )
