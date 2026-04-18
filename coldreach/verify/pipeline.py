"""
Email verification pipeline — chains individual checkers in order.

Steps (in order):
    1. Syntax       — RFC 5322 structure validation
    2. Disposable   — known throwaway domain blocklist
    3. DNS / MX     — async domain existence + MX record lookup
    4. Reacher      — SMTP verification via Reacher microservice (optional)
    5. Holehe       — platform-presence check across 120+ sites (optional, slow)

Each check contributes a ``score_delta`` to a running confidence score.
The pipeline stops early on a hard FAIL so downstream checks aren't wasted.

Score baseline
--------------
All emails start at a neutral baseline of 30. Checks add or subtract:

    Syntax PASS:         implied (no delta — just a gate)
    Not disposable:     +5
    MX records found:   +10
    SMTP valid:         +20  (Reacher — requires Docker service)
    Holehe platforms:   +15  (Holehe — slow, opt-in)
    Found on website:   +35  (source hint from crawler)

Final score is clamped to [0, 100].
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from coldreach.verify._types import CheckResult, CheckStatus
from coldreach.verify.disposable import check_disposable
from coldreach.verify.dns_check import check_dns
from coldreach.verify.holehe import check_holehe
from coldreach.verify.reacher import check_reacher
from coldreach.verify.syntax import check_syntax

logger = logging.getLogger(__name__)

# ── Score baseline ────────────────────────────────────────────────────────────
_BASELINE_SCORE = 30
"""Starting confidence score before any checker runs."""


# ---------------------------------------------------------------------------
# Pipeline result
# ---------------------------------------------------------------------------


@dataclass
class PipelineResult:
    """Aggregated result of all verification checks for one email address.

    Attributes
    ----------
    email:
        The raw input email (not normalised).
    checks:
        Ordered mapping of check name → CheckResult.
    base_score:
        Starting score before check deltas are applied.
    """

    email: str
    checks: dict[str, CheckResult] = field(default_factory=dict)
    base_score: int = _BASELINE_SCORE

    # ------------------------------------------------------------------
    # Computed properties
    # ------------------------------------------------------------------

    @property
    def normalized_email(self) -> str:
        """RFC-normalised email if syntax check passed, else raw input."""
        syntax = self.checks.get("syntax")
        if syntax and syntax.passed:
            normalized = syntax.metadata.get("normalized", self.email)
            return str(normalized)
        return self.email

    @property
    def score(self) -> int:
        """Final confidence score clamped to [0, 100]."""
        total = self.base_score + sum(r.score_delta for r in self.checks.values())
        return max(0, min(100, total))

    @property
    def passed(self) -> bool:
        """True if no check returned FAIL status."""
        return all(r.status != CheckStatus.FAIL for r in self.checks.values())

    @property
    def failed(self) -> bool:
        """True if at least one check returned FAIL status."""
        return not self.passed

    @property
    def mx_records(self) -> list[str]:
        """MX records returned by the DNS check, if available."""
        dns_result = self.checks.get("dns")
        if dns_result and not dns_result.failed:
            records = dns_result.metadata.get("mx_records", [])
            return list(records)
        return []

    @property
    def domain(self) -> str:
        """Domain part of the (normalised) email."""
        try:
            return self.normalized_email.split("@")[1]
        except IndexError:
            return ""

    @property
    def failure_reason(self) -> str | None:
        """Reason of the first failing check, if any."""
        for result in self.checks.values():
            if result.failed:
                return result.reason
        return None

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict (for JSON output)."""
        return {
            "email": self.email,
            "normalized": self.normalized_email,
            "passed": self.passed,
            "score": self.score,
            "mx_records": self.mx_records,
            "checks": {
                name: {
                    "status": check.status.value,
                    "reason": check.reason,
                    "score_delta": check.score_delta,
                }
                for name, check in self.checks.items()
            },
        }

    def __repr__(self) -> str:
        return (
            f"PipelineResult("
            f"email={self.normalized_email!r}, "
            f"passed={self.passed}, "
            f"score={self.score})"
        )


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------


async def run_basic_pipeline(
    email: str,
    *,
    dns_timeout: float = 5.0,
    reacher_url: str | None = None,
    reacher_timeout: float = 15.0,
    run_holehe: bool = False,
    holehe_timeout: float = 30.0,
) -> PipelineResult:
    """Run the full verification pipeline for one email address.

    Steps: syntax → disposable → DNS → Reacher (optional) → Holehe (optional).

    Parameters
    ----------
    email:
        The email address to verify.
    dns_timeout:
        Timeout in seconds for the DNS resolver.
    reacher_url:
        Base URL of the Reacher SMTP service (e.g. ``"http://localhost:8083"``).
        Pass ``None`` to skip SMTP verification.
    reacher_timeout:
        HTTP timeout for Reacher requests (SMTP handshakes can be slow).
    run_holehe:
        If True, check whether the email is registered on 120+ platforms.
        This is slow (15-45s) — only enable for high-value candidates.
    holehe_timeout:
        Per-request HTTP timeout for holehe module calls.
    """
    result = PipelineResult(email=email)

    # ── Step 1: Syntax ────────────────────────────────────────────────────────
    syntax_result = check_syntax(email)
    result.checks["syntax"] = syntax_result

    if syntax_result.failed:
        logger.debug("Pipeline stopped at syntax for %r", email)
        return result

    normalized = str(syntax_result.metadata.get("normalized", email))

    # ── Step 2: Disposable domain ─────────────────────────────────────────────
    disposable_result = check_disposable(normalized)
    result.checks["disposable"] = disposable_result

    if disposable_result.failed:
        logger.debug("Pipeline stopped at disposable for %r", normalized)
        return result

    # ── Step 3: DNS / MX records ──────────────────────────────────────────────
    dns_result = await check_dns(normalized, timeout=dns_timeout)
    result.checks["dns"] = dns_result

    if dns_result.failed:
        logger.debug("Pipeline stopped at DNS for %r", normalized)
        return result

    # ── Step 4: Reacher SMTP verification (optional) ─────────────────────────
    if reacher_url:
        reacher_result = await check_reacher(
            normalized,
            reacher_url=reacher_url,
            timeout=reacher_timeout,
        )
        result.checks["reacher"] = reacher_result
        if reacher_result.failed:
            logger.debug("Pipeline stopped at Reacher for %r", normalized)
            return result

    # ── Step 5: Holehe platform presence (optional, slow) ────────────────────
    if run_holehe:
        holehe_result = await check_holehe(normalized, timeout=holehe_timeout)
        result.checks["holehe"] = holehe_result

    logger.debug(
        "Pipeline complete for %r — passed=%s score=%d",
        normalized,
        result.passed,
        result.score,
    )
    return result
