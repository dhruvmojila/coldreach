"""
ColdReach local API server.

Exposes a FastAPI application on localhost:8765 so external tools — primarily
the Chrome extension — can call ColdReach without invoking the CLI directly.

Start with:
    coldreach serve          # default: localhost:8765
    coldreach serve --port 9000 --host 127.0.0.1

Endpoints
---------
POST /api/find              Discover emails; returns full DomainResult JSON.
POST /api/find/stream       Same but Server-Sent Events — emits as each source finishes.
POST /api/verify            Verify a single email; returns PipelineResult JSON.
GET  /api/status            Service health (reuses diagnostics module).
GET  /api/cache             List all cached domains.
DELETE /api/cache/{domain}  Remove one domain from cache.
GET  /api/version           Package version string.

Design decisions
----------------
- CORS is open to chrome-extension:// and localhost origins.
- The Chrome extension always passes quick=true (10s target vs 5min full scan).
- SSE stream emits one JSON event per source as it finishes, then a final
  "complete" event with the merged DomainResult.  Clients that don't need
  streaming can use POST /api/find and wait for the full response.
- No authentication — localhost only.  Binding to 0.0.0.0 is intentionally
  not supported; use a reverse proxy if you need network access.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from coldreach import __version__
from coldreach.core.finder import FinderConfig, find_emails
from coldreach.core.models import DomainResult
from coldreach.resolve.company import resolve_domain
from coldreach.sources.base import SourceResult
from coldreach.storage.cache import CacheStore
from coldreach.verify.pipeline import PipelineResult, run_basic_pipeline

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="ColdReach API",
    description="Local API server for the ColdReach email discovery tool.",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Allow Chrome extensions and localhost tooling to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://127.0.0.1",
        # Chrome extension origin prefix — the full ID is unknown at build time,
        # so we allow all chrome-extension:// origins.  The server is localhost-
        # only so there is no meaningful security boundary to preserve here.
        "chrome-extension://",
    ],
    allow_origin_regex=r"chrome-extension://.*",
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class FindRequest(BaseModel):
    """Parameters for a domain email discovery run."""

    domain: str | None = Field(None, description="Target domain, e.g. 'stripe.com'.")
    company: str | None = Field(None, description="Company name — resolves to a domain first.")
    name: str | None = Field(None, description="Person full name for pattern generation.")
    quick: bool = Field(
        True,
        description=(
            "Skip slow OSINT tools (theHarvester + SpiderFoot). "
            "Recommended for extension use — results in ~10s."
        ),
    )
    min_confidence: int = Field(0, ge=0, le=100, description="Hide emails below this score.")
    use_firecrawl: bool = Field(False, description="Enable Firecrawl JS scraping.")
    use_crawl4ai: bool = Field(False, description="Enable crawl4ai Playwright scraping.")
    no_cache: bool = Field(False, description="Skip cache read/write.")
    refresh: bool = Field(False, description="Ignore cache and re-run all sources.")


class VerifyRequest(BaseModel):
    """Parameters for single-email verification."""

    email: str = Field(..., description="Email address to verify.")
    run_holehe: bool = Field(False, description="Run Holehe platform check (slow).")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _finder_config(req: FindRequest) -> FinderConfig:
    """Build FinderConfig from an API request."""
    return FinderConfig(
        use_harvester=not req.quick,
        use_spiderfoot=not req.quick,
        use_firecrawl=req.use_firecrawl,
        use_crawl4ai=req.use_crawl4ai,
        use_cache=not req.no_cache,
        refresh_cache=req.refresh,
        min_confidence=req.min_confidence,
    )


def _sse_event(event: str, data: Any) -> str:
    """Format a single Server-Sent Event frame."""
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


async def _resolve(req: FindRequest) -> str:
    """Return the target domain, resolving company name if needed."""
    if req.domain:
        return req.domain.strip().lower().removeprefix("www.")
    if req.company:
        resolved = await resolve_domain(req.company)
        if not resolved:
            raise HTTPException(
                status_code=422,
                detail=f"Could not resolve a domain for company '{req.company}'. "
                "Pass --domain directly.",
            )
        return resolved
    raise HTTPException(status_code=422, detail="Provide 'domain' or 'company'.")


# ---------------------------------------------------------------------------
# Routes — discovery
# ---------------------------------------------------------------------------


@app.post("/api/find", response_model=None)
async def find(req: FindRequest) -> dict[str, Any]:
    """Discover emails for a domain.  Blocks until all sources complete.

    For live progress while sources are running, use ``POST /api/find/stream``.
    """
    domain = await _resolve(req)
    cfg = _finder_config(req)
    result: DomainResult = await find_emails(domain, person_name=req.name, config=cfg)
    return result.model_dump(mode="json")


@app.post("/api/find/stream")
async def find_stream(req: FindRequest) -> StreamingResponse:
    """Discover emails with Server-Sent Events.

    Emits one ``source`` event per completed source (with emails found so far),
    then a final ``complete`` event containing the full merged ``DomainResult``.

    Event types
    -----------
    ``progress``  — intermediate: ``{ source, found, total_so_far }``
    ``complete``  — final: full DomainResult JSON (same schema as POST /api/find)
    ``error``     — fatal: ``{ detail: "..." }``
    """
    return StreamingResponse(
        _stream_find(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering if proxied
        },
    )


async def _stream_find(req: FindRequest) -> AsyncIterator[str]:
    """Async generator that yields SSE frames for a find run."""
    try:
        domain = await _resolve(req)
    except HTTPException as exc:
        yield _sse_event("error", {"detail": exc.detail})
        return

    cfg = _finder_config(req)

    # We run find_emails() in a thread so the SSE connection stays open.
    # Progress events are emitted by hooking into the source execution loop
    # via a shared queue written to by a custom source wrapper.
    queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()

    async def _run() -> DomainResult:
        result = await _find_with_progress(domain, req.name, cfg, queue)
        await queue.put(None)  # sentinel: done
        return result

    task = asyncio.create_task(_run())

    # Stream progress events until sentinel received
    while True:
        event = await queue.get()
        if event is None:
            break
        yield _sse_event("progress", event)

    result = await task
    yield _sse_event("complete", result.model_dump(mode="json"))


async def _find_with_progress(
    domain: str,
    person_name: str | None,
    cfg: FinderConfig,
    queue: asyncio.Queue[dict[str, Any] | None],
) -> DomainResult:
    """Run find_emails and push progress events into *queue* as sources finish."""
    from coldreach.sources.base import BaseSource

    # Build source list inline (mirrors finder.py logic) so we can wrap each source.
    sources = _build_sources(cfg)

    sem = asyncio.Semaphore(cfg.max_concurrent_sources)
    all_raw: list[SourceResult] = []
    emails_seen: set[str] = set()

    async def _run_one(src: BaseSource) -> None:
        async with sem:
            results, summary = await src.run(domain, person_name=person_name)
            all_raw.extend(results)
            new_emails = [r.email for r in results if r.email not in emails_seen]
            emails_seen.update(new_emails)
            await queue.put(
                {
                    "source": src.name,
                    "found": len(results),
                    "new": len(new_emails),
                    "total_so_far": len(emails_seen),
                    "errors": summary.errors,
                }
            )

    await asyncio.gather(*[_run_one(s) for s in sources])

    # Run find_emails() with the original config — it handles cache, verification,
    # and scoring internally.  The SSE progress events above already gave the client
    # live source output; the final call gives properly scored + verified results.
    return await find_emails(domain, person_name=person_name, config=cfg)


def _build_sources(cfg: FinderConfig) -> list[Any]:  # BaseSource subclasses
    """Build the source list from a FinderConfig (mirrors finder.py)."""
    from coldreach.sources.base import BaseSource
    from coldreach.sources.crawl4ai_source import Crawl4AISource
    from coldreach.sources.firecrawl import FirecrawlSource
    from coldreach.sources.github import GitHubSource
    from coldreach.sources.harvester import HarvesterSource
    from coldreach.sources.reddit import RedditSource
    from coldreach.sources.search_engine import SearchEngineSource
    from coldreach.sources.spiderfoot import SpiderFootSource
    from coldreach.sources.web_crawler import WebCrawlerSource
    from coldreach.sources.whois_source import WhoisSource

    sources: list[BaseSource] = []
    if cfg.use_web_crawler:
        sources.append(WebCrawlerSource(timeout=cfg.request_timeout))
    if cfg.use_whois:
        sources.append(WhoisSource(timeout=cfg.request_timeout))
    if cfg.use_github:
        sources.append(GitHubSource(token=cfg.github_token, timeout=cfg.request_timeout))
    if cfg.use_reddit:
        sources.append(RedditSource(timeout=cfg.request_timeout))
    if cfg.use_search_engine:
        sources.append(
            SearchEngineSource(
                searxng_url=cfg.searxng_url,
                brave_api_key=cfg.brave_api_key,
                timeout=cfg.request_timeout,
            )
        )
    if cfg.use_harvester:
        sources.append(
            HarvesterSource(
                container=cfg.harvester_container,
                sources=cfg.harvester_sources,
                max_wait=cfg.harvester_max_wait,
            )
        )
    if cfg.use_spiderfoot:
        sources.append(
            SpiderFootSource(
                container=cfg.spiderfoot_container,
                max_wait=cfg.spiderfoot_max_wait,
            )
        )
    if cfg.use_firecrawl:
        sources.append(
            FirecrawlSource(firecrawl_url=cfg.firecrawl_url, timeout=cfg.request_timeout)
        )
    if cfg.use_crawl4ai:
        sources.append(Crawl4AISource(timeout=cfg.request_timeout))
    return sources


# ---------------------------------------------------------------------------
# Routes — verification
# ---------------------------------------------------------------------------


@app.post("/api/verify", response_model=None)
async def verify(req: VerifyRequest) -> dict[str, Any]:
    """Verify a single email address through the full pipeline."""
    from coldreach.config import get_settings

    cfg = get_settings()
    result: PipelineResult = await run_basic_pipeline(
        req.email,
        reacher_url=cfg.reacher_url,
        run_holehe=req.run_holehe,
    )
    return result.to_dict()


# ---------------------------------------------------------------------------
# Routes — status
# ---------------------------------------------------------------------------


@app.get("/api/status")
async def status() -> dict[str, Any]:
    """Return service health and optional package status."""
    from coldreach import diagnostics

    report = await diagnostics.run()
    return {
        "services": [
            {
                "name": s.name,
                "online": s.online,
                "latency_ms": s.latency_ms,
                "detail": s.detail,
                "role": s.role,
                "separate_stack": s.separate_stack,
            }
            for s in report.services
        ],
        "packages": [
            {
                "name": p.name,
                "installed": p.installed,
                "version": p.version,
            }
            for p in report.packages
        ],
        "summary": {
            "services_online": report.services_online,
            "packages_installed": report.packages_installed,
        },
    }


# ---------------------------------------------------------------------------
# Routes — cache
# ---------------------------------------------------------------------------


@app.get("/api/cache")
async def cache_list() -> dict[str, Any]:
    """List all cached domains."""
    store = CacheStore(db_path="~/.coldreach/cache.db")
    rows = store.list_domains()
    return {
        "domains": [
            {
                "domain": domain,
                "cached_at": cached_at.isoformat() if cached_at else None,
                "expired": expired,
            }
            for domain, cached_at, expired in rows
        ],
        "total": len(rows),
    }


@app.delete("/api/cache/{domain}")
async def cache_clear(domain: str) -> dict[str, Any]:
    """Remove a domain from the cache."""
    store = CacheStore(db_path="~/.coldreach/cache.db")
    store.clear(domain=domain)
    return {"success": True, "domain": domain}


# ---------------------------------------------------------------------------
# Routes — meta
# ---------------------------------------------------------------------------


@app.get("/api/version")
async def version() -> dict[str, str]:
    """Return the ColdReach package version."""
    return {"version": __version__}


@app.get("/")
async def root() -> dict[str, str]:
    """Health probe — returns 200 OK with a link to the API docs."""
    return {"status": "ok", "docs": "/docs", "version": __version__}
