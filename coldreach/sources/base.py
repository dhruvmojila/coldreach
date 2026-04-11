"""
Abstract base class for all ColdReach email discovery sources.

Every source follows the same contract:
  - Accepts a domain (and optionally a person name hint)
  - Returns a list of SourceResult objects
  - Never raises — catches its own errors and returns an empty list with a note

Sources are designed to run concurrently via asyncio.gather().
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from coldreach.core.models import EmailSource

logger = logging.getLogger(__name__)


@dataclass
class SourceResult:
    """A single email address found by a source.

    Attributes
    ----------
    email:
        The discovered email address (raw, not yet normalised).
    source:
        Which source found this email.
    url:
        The page or endpoint where the email was found.
    context:
        Surrounding text snippet that contained the email.
    confidence_hint:
        Optional score delta hint from the source (0 = no hint).
    """

    email: str
    source: EmailSource
    url: str = ""
    context: str = ""
    confidence_hint: int = 0


@dataclass
class SourceSummary:
    """Execution summary for one source run."""

    source_name: str
    found: int = 0
    errors: list[str] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str = ""


class BaseSource(ABC):
    """Abstract base for all email discovery sources.

    Subclasses must implement :meth:`fetch`.

    Parameters
    ----------
    timeout:
        HTTP / subprocess timeout in seconds.
    """

    #: Override in subclass to give the source a human-readable name.
    name: str = "unknown"

    def __init__(self, timeout: float = 10.0) -> None:
        self.timeout = timeout
        self._log = logging.getLogger(f"coldreach.sources.{self.name}")

    @abstractmethod
    async def fetch(
        self,
        domain: str,
        *,
        person_name: str | None = None,
    ) -> list[SourceResult]:
        """Discover emails for *domain*.

        Parameters
        ----------
        domain:
            The target domain, e.g. ``"stripe.com"``.
        person_name:
            Optional full name hint for pattern-based sources.

        Returns
        -------
        list[SourceResult]
            Discovered email addresses. Empty list if nothing found or on error.
        """

    async def run(
        self,
        domain: str,
        *,
        person_name: str | None = None,
    ) -> tuple[list[SourceResult], SourceSummary]:
        """Safe wrapper around :meth:`fetch` — never raises.

        Returns the results list and a summary suitable for logging/display.
        """
        summary = SourceSummary(source_name=self.name)
        try:
            results = await self.fetch(domain, person_name=person_name)
            summary.found = len(results)
            if results:
                self._log.debug("%s found %d email(s) for %s", self.name, len(results), domain)
        except Exception as exc:
            self._log.warning("%s failed for %s: %s", self.name, domain, exc)
            summary.errors.append(str(exc))
            results = []
        return results, summary
