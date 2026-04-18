"""
theHarvester source — CLI runner via docker exec.

Runs theHarvester inside the ``coldreach-theharvester`` container using
``docker exec``, capturing JSON output via a temp file.

CLI invocation inside the container:
    theHarvester \\
        -d <domain>          # target domain
        -b <sources>         # comma-separated source list, or "all"
        -l <limit>           # max results per source query
        -q                   # quiet: suppress missing API-key warnings
        -f /tmp/cr-<domain>  # write results to JSON + XML files

JSON output at /tmp/cr-<domain>.json:
    {"emails": [...], "hosts": [...], "shodan": [...]}

Free sources (no API key needed) — subset that reliably finds emails:
    duckduckgo, yahoo, baidu, crtsh, certspotter, hackertarget,
    rapiddns, dnsdumpster, urlscan, otx, thc, commoncrawl,
    waybackarchive, robtex, threatcrowd

API-key sources (set in ./theHarvester/theHarvester/data/api-keys.yaml):
    brave, github-code, hunter, virustotal, shodan, securityTrails, ...

Service: docker compose up theharvester   (builds from ./theHarvester/)
Swagger: http://localhost:5050/docs

Gracefully returns empty results if:
  - The Docker container is not running
  - The scan times out
  - docker is not available on the host
"""

from __future__ import annotations

import asyncio
import json
import logging
import re

from coldreach.core.models import EmailSource
from coldreach.sources.base import BaseSource, SourceResult

logger = logging.getLogger(__name__)

_CONTAINER_NAME = "coldreach-theharvester"

# Free sources that work without an API key and are likely to find emails.
_FREE_SOURCES = [
    "duckduckgo",
    "yahoo",
    "baidu",
    "crtsh",
    "certspotter",
    "hackertarget",
    "rapiddns",
    "dnsdumpster",
    "urlscan",
    "otx",
    "thc",
    "commoncrawl",
    "waybackarchive",
    "robtex",
    "threatcrowd",
]

# Regex: valid RFC-ish email local+domain
_VALID_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]{1,64}@[a-zA-Z0-9.\-]{1,253}\.[a-zA-Z]{2,}$")

# theHarvester sometimes emits HTML/JS unicode-escaped values as email local parts,
# e.g. "u003caccount@domain.com" which comes from "<account@domain.com>" being
# encoded as "\u003c". Reject local parts starting with u + 3-4 hex digits.
_HTML_ENTITY_PREFIX_RE = re.compile(r"^u[0-9a-f]{3,4}", re.IGNORECASE)


class HarvesterSource(BaseSource):
    """Run theHarvester CLI via ``docker exec`` and collect email addresses.

    Requires the ``theharvester`` Docker service to be running.
    Returns empty results gracefully if the container is unavailable.

    Parameters
    ----------
    container:
        Name of the running theHarvester Docker container.
    sources:
        Comma-separated source string passed to ``-b``.
        Defaults to all free (no-API-key) sources.
        Pass ``"all"`` to use every available source (many will be skipped
        silently if API keys are missing).
    limit:
        Maximum results per source query (``-l`` flag).
    max_wait:
        Maximum seconds to wait for the subprocess to finish.
    timeout:
        Kept for interface compatibility; not used for HTTP here.
    """

    name = "theharvester"

    def __init__(
        self,
        container: str = _CONTAINER_NAME,
        sources: str | None = None,
        limit: int = 500,
        max_wait: float = 120.0,
        timeout: float = 120.0,
    ) -> None:
        super().__init__(timeout=timeout)
        self.container = container
        self.sources = sources or ",".join(_FREE_SOURCES)
        self.limit = limit
        self.max_wait = max_wait

    async def fetch(
        self,
        domain: str,
        *,
        person_name: str | None = None,
    ) -> list[SourceResult]:
        emails = await self._run_cli(domain)
        return [
            SourceResult(
                email=email,
                source=EmailSource.THE_HARVESTER,
                url="",
                context=f"theHarvester CLI scan of {domain}",
                confidence_hint=20,
            )
            for email in emails
        ]

    async def _run_cli(self, domain: str) -> list[str]:
        """Run theHarvester inside the container, return domain-filtered emails."""
        safe_domain = re.sub(r"[^a-zA-Z0-9.\-]", "_", domain)
        out_path = f"/tmp/cr-{safe_domain}"

        cmd = [
            "docker",
            "exec",
            self.container,
            "theHarvester",
            "-d",
            domain,
            "-b",
            self.sources,
            "-l",
            str(self.limit),
            "-q",  # suppress missing API-key warnings
            "-f",
            out_path,  # write JSON + XML output files
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError:
            self._log.debug("theHarvester: 'docker' not found on PATH")
            return []
        except OSError as exc:
            self._log.debug("theHarvester: failed to launch docker exec: %s", exc)
            return []

        try:
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=self.max_wait)
        except TimeoutError:
            proc.kill()
            self._log.warning("theHarvester timed out after %ss for %s", self.max_wait, domain)
            return []

        if proc.returncode != 0:
            err = stderr.decode(errors="replace").strip()
            if "No such container" in err or "not running" in err.lower():
                self._log.debug(
                    "theHarvester container '%s' not running — is Docker up?",
                    self.container,
                )
            else:
                self._log.debug("theHarvester non-zero exit %d: %s", proc.returncode, err[:200])
            return []

        # Read JSON output file from inside the container
        return await self._read_json_output(out_path + ".json", domain)

    async def _read_json_output(self, json_path: str, domain: str) -> list[str]:
        """Read the JSON results file written by theHarvester -f flag."""
        read_cmd = ["docker", "exec", self.container, "cat", json_path]
        try:
            proc = await asyncio.create_subprocess_exec(
                *read_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10.0)
        except Exception as exc:
            self._log.debug("theHarvester: could not read output file: %s", exc)
            return []

        if proc.returncode != 0:
            self._log.debug("theHarvester: output file not found at %s", json_path)
            return []

        try:
            data = json.loads(stdout.decode(errors="replace"))
        except json.JSONDecodeError:
            self._log.debug("theHarvester: invalid JSON in output file")
            return []

        raw_emails: list[str] = data.get("emails") or []
        return self._filter_emails(raw_emails, domain)

    def _filter_emails(self, raw: list[str], domain: str) -> list[str]:
        """Normalise, domain-filter, and deduplicate email list."""
        domain_lower = domain.lower()
        seen: set[str] = set()
        result: list[str] = []

        for email in raw:
            email = email.strip().lower()
            if not email or email in seen:
                continue
            if not _VALID_EMAIL_RE.match(email):
                continue
            local = email.split("@")[0]
            if _HTML_ENTITY_PREFIX_RE.match(local):
                continue
            if not (email.endswith(f"@{domain_lower}") or email.endswith(f".{domain_lower}")):
                continue
            seen.add(email)
            result.append(email)

        self._log.debug(
            "theHarvester: %d raw emails → %d domain-matched for %s",
            len(raw),
            len(result),
            domain,
        )
        return result
