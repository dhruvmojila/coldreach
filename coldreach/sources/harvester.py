"""
theHarvester source — subprocess wrapper around the theHarvester OSINT tool.

theHarvester scans multiple public sources (Google, Bing, DuckDuckGo,
crt.sh, HackerTarget, PGP keyservers, etc.) and extracts emails and
subdomains. It must be installed separately: `pip install theHarvester`
or via the Docker Compose stack.

Strategy:
  - Runs: theHarvester -d <domain> -b all -l 100
  - Parses stdout for email addresses
  - Falls back gracefully if theHarvester is not installed

Sources used by default: google, bing, duckduckgo, crtsh, hackertarget,
pgp, certspotter, rapiddns.
"""

from __future__ import annotations

import asyncio
import re
import shutil

from coldreach.core.models import EmailSource
from coldreach.sources.base import BaseSource, SourceResult

_EMAIL_RE = re.compile(
    r"([a-zA-Z0-9._%+\-]{1,64}@[a-zA-Z0-9.\-]{1,253}\.[a-zA-Z]{2,})",
    re.IGNORECASE,
)

# Safe default sources — avoids LinkedIn (TOS) and slow/broken ones
_DEFAULT_SOURCES = "bing,duckduckgo,crtsh,hackertarget,pgp,certspotter,rapiddns"


def _is_available() -> bool:
    """Return True if theHarvester binary is on PATH."""
    return shutil.which("theHarvester") is not None


def _parse_emails(output: str, domain: str) -> list[str]:
    """Extract unique emails belonging to *domain* from theHarvester stdout."""
    seen: set[str] = set()
    result: list[str] = []
    for m in _EMAIL_RE.finditer(output):
        email = m.group(1).strip().lower()
        if email in seen:
            continue
        if email.endswith(f"@{domain}") or email.endswith(f".{domain}"):
            seen.add(email)
            result.append(email)
    return result


class HarvesterSource(BaseSource):
    """Run theHarvester CLI and extract emails from its output.

    Silently returns empty results if theHarvester is not installed —
    it is an optional tool in the stack.

    Parameters
    ----------
    sources:
        Comma-separated list of theHarvester data sources to use.
    limit:
        Maximum results per source (passed as ``-l``).
    timeout:
        Subprocess timeout in seconds.
    """

    name = "theharvester"

    def __init__(
        self,
        sources: str = _DEFAULT_SOURCES,
        limit: int = 100,
        timeout: float = 60.0,
    ) -> None:
        super().__init__(timeout=timeout)
        self.sources = sources
        self.limit = limit

    async def fetch(
        self,
        domain: str,
        *,
        person_name: str | None = None,
    ) -> list[SourceResult]:
        if not _is_available():
            self._log.debug("theHarvester not found on PATH — skipping")
            return []

        cmd = [
            "theHarvester",
            "-d",
            domain,
            "-b",
            self.sources,
            "-l",
            str(self.limit),
        ]

        self._log.debug("Running: %s", " ".join(cmd))

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_bytes, _ = await asyncio.wait_for(proc.communicate(), timeout=self.timeout)
        except TimeoutError:
            self._log.warning("theHarvester timed out after %ss for %s", self.timeout, domain)
            return []
        except OSError as exc:
            self._log.warning("theHarvester subprocess error: %s", exc)
            return []

        output = stdout_bytes.decode("utf-8", errors="replace")
        emails = _parse_emails(output, domain)

        self._log.debug("theHarvester found %d email(s) for %s", len(emails), domain)

        return [
            SourceResult(
                email=email,
                source=EmailSource.THE_HARVESTER,
                url="",
                context="theHarvester OSINT scan",
                confidence_hint=20,
            )
            for email in emails
        ]
