"""
SpiderFoot source — REST API client with incremental result streaming.

Uses SpiderFoot's built-in CherryPy REST API (localhost:5001) instead of
docker exec.  This gives us real-time results as the scan progresses:

  1. POST /startscan  → get scan_id immediately
  2. Poll GET /scaneventresults?id=SCAN_ID&eventType=EMAILADDR every 15s
  3. Emit each new email as it appears (streaming-friendly)
  4. GET /stopscan?id=SCAN_ID when done/timeout reached

Why not docker exec sf.py?
  - sf.py outputs ALL results only at the very end (no streaming)
  - The scan continues running in SpiderFoot's DB even after we kill docker exec
  - No way to cancel from Python side
  - REST API solves all three problems

Key endpoints confirmed working (SpiderFoot v4.0.0):
  GET  /ping                                → ["SUCCESS", "4.0.0"]
  GET  /scanlist                            → list of all scans
  POST /startscan  (form data)              → ["SUCCESS", "SCAN_ID"]
  GET  /scaneventresults?id=ID&eventType=X  → [[...], [...]] rows
  GET  /scanstatus?id=ID                    → [name, target, started, ...]
  GET  /stopscan?id=ID                      → stops the scan

Modules used (fast, no API keys, effective):
  sfp_pgp        — PGP keyservers: finds 20+ emails per domain in ~60s
  sfp_emailformat — email-format.com database: instant
  sfp_whois      — WHOIS registrant: instant
  sfp_email      — extracts emails from any content fed by other modules
  sfp_citadel    — breach/enrichment databases (free sources: PeopleDataLabs)
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import AsyncIterator

import httpx

from coldreach.core.models import EmailSource
from coldreach.sources.base import BaseSource, SourceResult

logger = logging.getLogger(__name__)

_API_BASE = "http://localhost:5001"
_HEADERS_JSON = {"Accept": "application/json"}

# Email-focused modules — confirmed to work in < 5 min
_EMAIL_MODULES = ",".join(
    [
        "sfp_pgp",  # PGP keyservers — finds 20+ emails in ~60s
        "sfp_emailformat",  # email-format.com — instant
        "sfp_whois",  # WHOIS registrant — instant
        "sfp_email",  # extracts emails from content fed by other modules
        "sfp_citadel",  # breach/enrichment — finds named emails from data sources
    ]
)

_EMAIL_EVENT_TYPES = ",".join(
    [
        "EMAILADDR",
        "EMAILADDR_GENERIC",
        "EMAILADDR_DELIVERABLE",
        "EMAILADDR_COMPROMISED",  # sfp_citadel breach data — valuable leads
    ]
)

# How long to poll before giving up and stopping the scan
_MAX_SCAN_SECONDS = 480.0  # 8 minutes hard limit
_POLL_INTERVAL = 15.0  # check for new results every 15s

# Basic email regex for domain filtering
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")


class SpiderFootSource(BaseSource):
    """Email discovery via SpiderFoot REST API with incremental streaming.

    Creates a scan via SpiderFoot's REST API, polls for results every 15s,
    and yields emails as they are found.  Stops the scan when done or after
    the configured timeout.

    Parameters
    ----------
    api_base:
        SpiderFoot web server base URL.
    max_wait:
        Maximum seconds before the scan is aborted.
    timeout:
        HTTP request timeout for individual API calls.
    """

    name = "spiderfoot"

    def __init__(
        self,
        api_base: str = _API_BASE,
        max_wait: float = _MAX_SCAN_SECONDS,
        # Kept for FinderConfig compatibility
        container: str = "coldreach-spiderfoot",
        timeout: float = 30.0,
    ) -> None:
        super().__init__(timeout=timeout)
        self.api_base = api_base.rstrip("/")
        self.max_wait = max_wait

    async def fetch(
        self,
        domain: str,
        *,
        person_name: str | None = None,
    ) -> list[SourceResult]:
        """Run scan and return all found emails (blocking until done or timeout)."""
        results: list[SourceResult] = []
        async for r in self.fetch_stream(domain):
            results.append(r)
        return results

    async def fetch_stream(
        self,
        domain: str,
        *,
        person_name: str | None = None,
    ) -> AsyncIterator[SourceResult]:
        """Stream email results as they are found by SpiderFoot.

        Yields a SourceResult each time SpiderFoot discovers a new email,
        allowing callers to forward results to SSE streams immediately.
        """
        if not await self._is_available():
            self._log.debug(
                "SpiderFoot not reachable at %s — is the container running?",
                self.api_base,
            )
            return

        scan_id = await self._start_scan(domain)
        if not scan_id:
            self._log.debug("SpiderFoot: failed to start scan for %s", domain)
            return

        self._log.info("SpiderFoot: scan %s started for %s", scan_id, domain)

        domain_lower = domain.lower()
        seen_emails: set[str] = set()
        elapsed = 0.0

        try:
            while elapsed < self.max_wait:
                await asyncio.sleep(_POLL_INTERVAL)
                elapsed += _POLL_INTERVAL

                # Check if scan is still running
                status = await self._scan_status(scan_id)
                self._log.debug(
                    "SpiderFoot scan %s: status=%s elapsed=%.0fs", scan_id, status, elapsed
                )

                # Fetch all current EMAILADDR results
                rows = await self._fetch_results(scan_id)
                for row in rows:
                    # Row format: [event_type, data, source_module, ...]
                    if isinstance(row, (list, tuple)) and len(row) >= 2:
                        raw_email = str(row[1]).strip().lower()
                    else:
                        continue

                    # Strip trailing annotations like " [apollo.io]"
                    email = raw_email.split("[")[0].strip()

                    if not _EMAIL_RE.match(email):
                        continue
                    if "@" not in email or email in seen_emails:
                        continue
                    if not (
                        email.endswith(f"@{domain_lower}") or email.endswith(f".{domain_lower}")
                    ):
                        continue

                    seen_emails.add(email)
                    yield SourceResult(
                        email=email,
                        source=EmailSource.SPIDERFOOT,
                        url=self.api_base,
                        context=f"SpiderFoot: {str(row[2]).strip() if len(row) > 2 else ''}",
                        confidence_hint=25,
                    )

                if status in ("FINISHED", "ERROR", "ABORTED"):
                    self._log.info(
                        "SpiderFoot scan %s finished (%s) — %d emails, %.0fs",
                        scan_id,
                        status,
                        len(seen_emails),
                        elapsed,
                    )
                    break

        finally:
            # Always stop the scan — avoids orphaned scans in the SpiderFoot UI
            await self._stop_scan(scan_id)

    # ── REST API helpers ──────────────────────────────────────────────────────

    async def _is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as c:
                resp = await c.get(f"{self.api_base}/ping", headers=_HEADERS_JSON)
                return resp.status_code == 200
        except Exception:
            return False

    async def _start_scan(self, domain: str) -> str | None:
        """POST /startscan → scan_id or None on failure."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as c:
                resp = await c.post(
                    f"{self.api_base}/startscan",
                    headers=_HEADERS_JSON,
                    data={
                        "scanname": f"coldreach-{domain}",
                        "scantarget": domain,
                        "modulelist": _EMAIL_MODULES,
                        "typelist": _EMAIL_EVENT_TYPES,
                        "usecase": "all",
                    },
                )
            payload = resp.json()
            if isinstance(payload, list) and payload[0] == "SUCCESS":
                return str(payload[1])
            self._log.debug("SpiderFoot startscan failed: %s", payload)
        except Exception as exc:
            self._log.debug("SpiderFoot startscan error: %s", exc)
        return None

    async def _scan_status(self, scan_id: str) -> str:
        """GET /scanstatus → status string (RUNNING / FINISHED / ERROR / ...)."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as c:
                resp = await c.get(
                    f"{self.api_base}/scanstatus",
                    params={"id": scan_id},
                    headers=_HEADERS_JSON,
                )
            data = resp.json()
            # Row: [name, target, started, updated, status, ...]
            if isinstance(data, list) and len(data) >= 5:
                return str(data[4])
        except Exception:
            pass
        return "UNKNOWN"

    async def _fetch_results(self, scan_id: str) -> list[list[object]]:
        """GET /scaneventresults → list of result rows."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as c:
                resp = await c.get(
                    f"{self.api_base}/scaneventresults",
                    params={"id": scan_id, "eventType": "EMAILADDR"},
                    headers=_HEADERS_JSON,
                )
            data = resp.json()
            if isinstance(data, list):
                return data
        except Exception as exc:
            self._log.debug("SpiderFoot fetch_results error: %s", exc)
        return []

    async def _stop_scan(self, scan_id: str) -> None:
        """GET /stopscan — best-effort, never raises."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as c:
                await c.get(
                    f"{self.api_base}/stopscan",
                    params={"id": scan_id},
                    headers=_HEADERS_JSON,
                )
        except Exception:
            pass

    # ── Parsing ───────────────────────────────────────────────────────────────

    def _parse_output(self, raw: str, domain: str) -> list[str]:
        """Parse a JSON string of result rows into domain-filtered emails.

        Handles:
        - Row format: ["EMAILADDR", "email@domain.com", "module"]
        - Dict format: {"type": "Email Address", "data": "email@domain.com"}
        - Emails with annotations: "email@domain.com [apollo.io]"
        - Partial/truncated JSON (scan killed mid-write)
        """
        import json as _json

        raw = raw.strip()
        if not raw:
            return []

        rows: list[object] = []
        try:
            rows = _json.loads(raw)
        except _json.JSONDecodeError:
            # Scan killed mid-write — try common truncation patterns
            for closer in ("]]", "]", "\n]]", "\n]"):
                try:
                    rows = _json.loads(raw.rstrip(",\n ") + closer)
                    break
                except _json.JSONDecodeError:
                    continue

        if not rows or not isinstance(rows, list):
            return []

        domain_lower = domain.lower()
        seen: set[str] = set()
        result: list[str] = []

        for row in rows:
            if isinstance(row, (list, tuple)) and len(row) >= 2:
                etype = str(row[0]).strip().upper()
                raw_data = str(row[1]).strip().lower()
            elif isinstance(row, dict):
                etype = str(row.get("type", "")).strip().upper()
                raw_data = str(row.get("data", "")).strip().lower()
            else:
                continue

            if etype not in (
                "EMAILADDR",
                "EMAIL ADDRESS",
                "EMAILADDR_GENERIC",
                "EMAILADDR_COMPROMISED",
                "EMAILADDR_DELIVERABLE",
            ):
                continue

            # Strip trailing annotations: "user@acme.com [apollo.io]" → "user@acme.com"
            email = raw_data.split("[")[0].strip()

            if not _EMAIL_RE.match(email) or "@" not in email or email in seen:
                continue
            if not (email.endswith(f"@{domain_lower}") or email.endswith(f".{domain_lower}")):
                continue

            seen.add(email)
            result.append(email)

        return result
