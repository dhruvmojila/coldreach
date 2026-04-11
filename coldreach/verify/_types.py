"""
Internal types for the verification pipeline.

``CheckResult`` is the standard return type of every checker function.
It carries a pass/fail status, a human-readable reason, a score delta that
feeds into the final confidence score, and an open-ended metadata dict for
checker-specific data (e.g. MX records, platform list).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class CheckStatus(StrEnum):
    """Outcome of a single verification check."""

    PASS = "pass"
    """The check passed — email looks good for this criterion."""
    FAIL = "fail"
    """The check failed — email should be discarded or heavily penalised."""
    WARN = "warn"
    """The check raised a concern but did not hard-fail."""
    SKIP = "skip"
    """The check was not applicable or the service was unavailable."""


@dataclass(slots=True)
class CheckResult:
    """Result of a single verification check.

    Attributes
    ----------
    status:
        Pass, fail, warn, or skip.
    reason:
        Human-readable explanation — shown in CLI output.
    score_delta:
        Amount to add to (positive) or subtract from (negative) the running
        confidence score. Checkers that are informational only use ``0``.
    metadata:
        Checker-specific extra data (e.g. ``{"mx_records": [...]}``).
    """

    status: CheckStatus
    reason: str = ""
    score_delta: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Boolean helpers
    # ------------------------------------------------------------------

    @property
    def passed(self) -> bool:
        """True if status is PASS."""
        return self.status == CheckStatus.PASS

    @property
    def failed(self) -> bool:
        """True if status is FAIL."""
        return self.status == CheckStatus.FAIL

    @property
    def warned(self) -> bool:
        """True if status is WARN."""
        return self.status == CheckStatus.WARN

    @property
    def skipped(self) -> bool:
        """True if status is SKIP."""
        return self.status == CheckStatus.SKIP

    # ------------------------------------------------------------------
    # Factory class-methods for clean, readable construction
    # ------------------------------------------------------------------

    @classmethod
    def pass_(
        cls,
        reason: str = "",
        score_delta: int = 0,
        **metadata: Any,
    ) -> CheckResult:
        """Create a passing result."""
        return cls(CheckStatus.PASS, reason, score_delta, dict(metadata))

    @classmethod
    def fail(
        cls,
        reason: str,
        score_delta: int = 0,
        **metadata: Any,
    ) -> CheckResult:
        """Create a failing result."""
        return cls(CheckStatus.FAIL, reason, score_delta, dict(metadata))

    @classmethod
    def warn(
        cls,
        reason: str,
        score_delta: int = 0,
        **metadata: Any,
    ) -> CheckResult:
        """Create a warning result."""
        return cls(CheckStatus.WARN, reason, score_delta, dict(metadata))

    @classmethod
    def skip(cls, reason: str = "service unavailable") -> CheckResult:
        """Create a skipped result."""
        return cls(CheckStatus.SKIP, reason, 0, {})

    def __repr__(self) -> str:
        return (
            f"CheckResult(status={self.status!r}, "
            f"reason={self.reason!r}, "
            f"score_delta={self.score_delta})"
        )
