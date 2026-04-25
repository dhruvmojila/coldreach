"""
ColdReach diagnostics — service availability and package install checks.

Used by `coldreach status` to give a quick health overview of all
Docker services and optional Python dependencies.
"""

from __future__ import annotations

import asyncio
import contextlib
import importlib.metadata
import importlib.util
import time
from dataclasses import dataclass, field

# ── Data models ───────────────────────────────────────────────────────────────


@dataclass
class ServiceResult:
    """Result of a single HTTP health check against a Docker service."""

    name: str
    url: str
    role: str  # one-liner describing what the service does
    separate_stack: bool = False  # True = not in the default compose stack
    online: bool = False
    latency_ms: int | None = None
    detail: str = ""


@dataclass
class PackageResult:
    """Install status of an optional Python package."""

    name: str
    import_name: str
    install_hint: str
    installed: bool = False
    version: str = ""


@dataclass
class DiagnosticsReport:
    """Aggregated result from a full diagnostics run."""

    services: list[ServiceResult] = field(default_factory=list)
    packages: list[PackageResult] = field(default_factory=list)

    @property
    def services_online(self) -> int:
        return sum(1 for s in self.services if s.online)

    @property
    def packages_installed(self) -> int:
        return sum(1 for p in self.packages if p.installed)


# ── Service definitions ───────────────────────────────────────────────────────

_SERVICES: list[tuple[str, str, str, bool]] = [
    # (name, url, role, separate_stack)
    ("SearXNG", "http://localhost:8088", "Metasearch engine (40+ sources)", False),
    ("Reacher", "http://localhost:8083", "SMTP email verifier (Rust)", False),
    ("SpiderFoot", "http://localhost:5001", "Deep OSINT (200+ modules)", False),
    ("theHarvester", "http://localhost:5050/docs", "Multi-source email harvester", False),
    # Firecrawl is NOT part of the default docker-compose stack — it needs its
    # own multi-service setup. See: https://github.com/mendableai/firecrawl
    ("Firecrawl", "http://localhost:3002", "JS scraper (optional — separate stack)", True),
]

# ── Package definitions ───────────────────────────────────────────────────────

_PACKAGES: list[tuple[str, str, str]] = [
    ("holehe", "holehe", "pip install coldreach[full]"),
    ("crawl4ai", "crawl4ai", "pip install crawl4ai && crawl4ai-setup"),
    ("firecrawl-py", "firecrawl", "pip install firecrawl-py"),
]


# ── Checks ────────────────────────────────────────────────────────────────────


async def _ping(
    name: str, url: str, role: str, separate_stack: bool = False, timeout: float = 5.0
) -> ServiceResult:
    """HTTP GET with timing; never raises."""
    import httpx

    result = ServiceResult(name=name, url=url, role=role, separate_stack=separate_stack)
    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url, follow_redirects=True)
        result.latency_ms = int((time.monotonic() - t0) * 1000)
        result.online = resp.status_code < 500
        result.detail = f"HTTP {resp.status_code}"
    except httpx.RemoteProtocolError:
        # Service is listening but has no HTTP root endpoint (e.g. Reacher SMTP API).
        # Port reachable = effectively online.
        result.online = True
        result.latency_ms = int((time.monotonic() - t0) * 1000)
        result.detail = "port open"
    except httpx.ConnectError:
        result.detail = "connection refused"
    except httpx.TimeoutException:
        result.detail = "timed out"
    except Exception as exc:
        result.detail = str(exc)[:60]
    return result


def _check_package(name: str, import_name: str, install_hint: str) -> PackageResult:
    result = PackageResult(name=name, import_name=import_name, install_hint=install_hint)
    if importlib.util.find_spec(import_name) is not None:
        result.installed = True
        with contextlib.suppress(importlib.metadata.PackageNotFoundError):
            result.version = importlib.metadata.version(name)
    return result


async def run(url_overrides: dict[str, str] | None = None) -> DiagnosticsReport:
    """Run all checks concurrently and return a DiagnosticsReport.

    Parameters
    ----------
    url_overrides:
        Map of service name → URL to override the defaults
        (e.g. ``{"SearXNG": "http://searxng:8080"}`` for Docker networks).
    """
    overrides = url_overrides or {}
    service_tasks = [
        _ping(name, overrides.get(name, url), role, separate_stack, timeout=5.0)
        for name, url, role, separate_stack in _SERVICES
    ]
    services = list(await asyncio.gather(*service_tasks))
    packages = [_check_package(name, imp, hint) for name, imp, hint in _PACKAGES]
    return DiagnosticsReport(services=services, packages=packages)


async def quick_service_check(timeout: float = 3.0) -> dict[str, bool]:
    """Ping core services (not separate-stack) and return {name: online}.

    Fast path for the find command — skips Firecrawl and other opt-in services.
    """
    service_tasks = [
        _ping(name, url, role, separate_stack, timeout=timeout)
        for name, url, role, separate_stack in _SERVICES
        if not separate_stack
    ]
    results = await asyncio.gather(*service_tasks)
    return {r.name: r.online for r in results}
