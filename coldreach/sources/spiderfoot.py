"""
SpiderFoot source — CLI runner via docker exec.

Runs sf.py inside the ``coldreach-spiderfoot`` container using
``docker exec``, capturing JSON output directly.  This avoids the
CherryPy web API entirely (which requires modules pre-loaded in config).

CLI invocation inside the container:
    /opt/venv/bin/python sf.py \\
        -s <domain>          # target
        -t EMAILADDR         # only collect email address events
        -u passive           # passive modules only — no active probing
        -o json              # structured output
        -q                   # quiet — suppress progress noise
        -x                   # strict: only modules that directly consume domain

Output is a JSON array of [event_type, data, source_module, ...] rows.
We filter rows where event_type == "EMAILADDR" and data ends with @domain.

Service: docker compose up spiderfoot   (builds from ./spiderfoot/)
Web UI:  http://localhost:5001/          (for browsing past scan results)

Gracefully returns empty results if:
  - The Docker container is not running
  - The scan times out
  - docker is not available on the host
"""

from __future__ import annotations

import asyncio
import json
import logging

from coldreach.core.models import EmailSource
from coldreach.sources.base import BaseSource, SourceResult

logger = logging.getLogger(__name__)

_CONTAINER_NAME = "coldreach-spiderfoot"
_SF_PYTHON = "/opt/venv/bin/python"
_SF_SCRIPT = "sf.py"
_SF_WORKDIR = "/home/spiderfoot"

# Maximum seconds to wait for the passive scan to complete
_MAX_WAIT = 300.0


class SpiderFootSource(BaseSource):
    """Run a SpiderFoot passive scan via ``docker exec`` and collect emails.

    Requires the ``spiderfoot`` Docker service to be running.
    Returns empty results gracefully if the container is unavailable.

    Parameters
    ----------
    container:
        Name of the running SpiderFoot Docker container.
    max_wait:
        Maximum seconds to wait for the scan subprocess to finish.
    timeout:
        Kept for interface compatibility; not used for HTTP here.
    """

    name = "spiderfoot"

    def __init__(
        self,
        container: str = _CONTAINER_NAME,
        max_wait: float = _MAX_WAIT,
        timeout: float = 15.0,
    ) -> None:
        super().__init__(timeout=timeout)
        self.container = container
        self.max_wait = max_wait

    async def fetch(
        self,
        domain: str,
        *,
        person_name: str | None = None,
    ) -> list[SourceResult]:
        emails = await self._run_cli(domain)
        self._log.debug("SpiderFoot found %d email(s) for %s", len(emails), domain)
        return [
            SourceResult(
                email=email,
                source=EmailSource.SPIDERFOOT,
                url="",
                context=f"SpiderFoot passive CLI scan of {domain}",
                confidence_hint=25,
            )
            for email in emails
        ]

    async def _run_cli(self, domain: str) -> list[str]:
        """Run sf.py inside the container via docker exec, return domain emails."""
        cmd = [
            "docker",
            "exec",
            "-w",
            _SF_WORKDIR,
            self.container,
            _SF_PYTHON,
            _SF_SCRIPT,
            "-s",
            domain,
            "-t",
            "EMAILADDR",
            "-u",
            "passive",  # passive: no active probing / port scanning
            "-o",
            "json",
            "-f",  # filter output to only the requested -t types
            "-q",  # quiet — suppress progress noise to stderr
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError:
            self._log.debug("SpiderFoot: 'docker' not found on PATH")
            return []
        except OSError as exc:
            self._log.debug("SpiderFoot: failed to launch docker exec: %s", exc)
            return []

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self.max_wait)
        except TimeoutError:
            proc.kill()
            self._log.warning("SpiderFoot scan timed out after %ss for %s", self.max_wait, domain)
            return []

        if proc.returncode != 0:
            err = stderr.decode(errors="replace").strip()
            if "No such container" in err or "not running" in err.lower():
                self._log.debug(
                    "SpiderFoot container '%s' not running — is Docker up?",
                    self.container,
                )
            else:
                self._log.debug("SpiderFoot non-zero exit %d: %s", proc.returncode, err[:200])
            return []

        return self._parse_output(stdout.decode(errors="replace"), domain)

    def _parse_output(self, raw: str, domain: str) -> list[str]:
        """Parse sf.py JSON output, returning domain-filtered email list."""
        raw = raw.strip()
        if not raw:
            return []

        try:
            rows = json.loads(raw)
        except json.JSONDecodeError:
            self._log.debug("SpiderFoot: could not parse JSON output")
            return []

        domain_lower = domain.lower()
        seen: set[str] = set()
        result: list[str] = []

        for row in rows:
            # Row format from sf.py -o json: [event_type, data, source, ...]
            if isinstance(row, list) and len(row) >= 2:
                etype = str(row[0]).upper()
                data = str(row[1]).strip().lower()
            elif isinstance(row, dict):
                etype = str(row.get("type", "")).upper()
                data = str(row.get("data", "")).strip().lower()
            else:
                continue

            if etype != "EMAILADDR":
                continue
            if "@" not in data or data in seen:
                continue
            if not (data.endswith(f"@{domain_lower}") or data.endswith(f".{domain_lower}")):
                continue
            seen.add(data)
            result.append(data)

        return result
