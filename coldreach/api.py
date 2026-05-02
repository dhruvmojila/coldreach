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
import secrets
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from coldreach import __version__
from coldreach.core.finder import FinderConfig, find_emails
from coldreach.core.models import DomainResult
from coldreach.resolve.company import resolve_domain
from coldreach.sources.base import BaseSource, SourceResult
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
# Job system — in-process pub/sub for long-running scans
# ---------------------------------------------------------------------------
# Each scan is a "job": sources push events into a queue, SSE drains it.
# The SSE connection stays open until the job completes or is cancelled,
# delivering emails one-at-a-time as every source finds them.


@dataclass
class ScanJob:
    """In-flight scan job with a live event queue."""

    job_id: str
    domain: str
    queue: asyncio.Queue[dict[str, Any] | None] = field(default_factory=asyncio.Queue)
    tasks: list[asyncio.Task[Any]] = field(default_factory=list)
    cancelled: bool = False
    # Accumulated emails — allows polling even without long-lived SSE
    emails: list[dict[str, Any]] = field(default_factory=list)
    sources_done: list[str] = field(default_factory=list)
    done: bool = False


# Active jobs keyed by job_id.  Completed jobs are cleaned up after streaming.
_jobs: dict[str, ScanJob] = {}


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class FindRequest(BaseModel):
    """Parameters for a domain email discovery run."""

    domain: str | None = Field(None, description="Target domain, e.g. 'stripe.com'.")
    company: str | None = Field(None, description="Company name — resolves to a domain first.")
    name: str | None = Field(None, description="Person full name for pattern generation.")
    quick: bool = Field(
        False,
        description=(
            "Skip slow OSINT tools (theHarvester + SpiderFoot). ~10s. "
            "Default False — use all sources for best results."
        ),
    )
    full_scan: bool = Field(
        False,
        description=(
            "Enable ALL sources including Firecrawl, Crawl4AI, theHarvester, "
            "SpiderFoot. Overrides quick=True. Takes 2-5 minutes."
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


def _finder_config(req: FindRequest, background_slow: bool = False) -> FinderConfig:
    """Build FinderConfig from an API request.

    full_scan=True overrides quick and enables all heavyweight sources.
    quick=True skips theHarvester, SpiderFoot, Firecrawl, Crawl4AI.
    Default (both False) runs all core sources; slow ones run in background
    when background_slow=True so fast results arrive in ~30s.
    """
    if req.full_scan:
        return FinderConfig(
            use_harvester=True,
            use_spiderfoot=True,
            use_firecrawl=True,
            use_crawl4ai=req.use_crawl4ai,
            use_cache=not req.no_cache,
            refresh_cache=req.refresh,
            min_confidence=req.min_confidence,
            background_slow_sources=background_slow,
        )
    return FinderConfig(
        use_harvester=not req.quick,
        use_spiderfoot=not req.quick,
        use_firecrawl=req.use_firecrawl,
        use_crawl4ai=req.use_crawl4ai,
        use_cache=not req.no_cache,
        refresh_cache=req.refresh,
        min_confidence=req.min_confidence,
        background_slow_sources=background_slow,
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

    # SSE stream uses background_slow=True: fast sources emit events immediately
    # (~30s), then SpiderFoot/Harvester continue in background updating the cache.
    cfg = _finder_config(req, background_slow=True)
    sources = _build_sources(cfg)

    # Emit start event immediately so the client knows total_sources for
    # the 0-100% progress bar before any source has run.
    yield _sse_event(
        "start",
        {
            "domain": domain,
            "total_sources": len(sources),
            "source_names": [s.name for s in sources],
            "mode": "full_scan" if req.full_scan else ("quick" if req.quick else "standard"),
        },
    )

    queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()

    async def _run() -> DomainResult:
        result = await _find_with_progress(domain, req.name, cfg, queue, sources)
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
    sources: list[Any],  # pre-built by caller so start event can report count
) -> DomainResult:
    """Run find_emails and push progress events into *queue* as sources finish."""

    sem = asyncio.Semaphore(cfg.max_concurrent_sources)
    all_raw: list[SourceResult] = []
    emails_seen: set[str] = set()
    sources_done = 0
    total = len(sources)

    async def _run_one(src: BaseSource) -> None:
        nonlocal sources_done
        async with sem:
            results, summary = await src.run(domain, person_name=person_name)
            all_raw.extend(results)
            new_emails = [r.email for r in results if r.email not in emails_seen]
            emails_seen.update(new_emails)
            sources_done += 1
            await queue.put(
                {
                    "source": src.name,
                    "found": len(results),
                    "new": len(new_emails),
                    "total_so_far": len(emails_seen),
                    "sources_done": sources_done,
                    "sources_total": total,
                    "percent": round(sources_done / total * 100) if total else 100,
                    "errors": summary.errors,
                    "skipped": summary.skipped,
                }
            )

    await asyncio.gather(*[_run_one(s) for s in sources])

    # Run find_emails() with the original config — it handles cache, verification,
    # and scoring internally.  The SSE progress events above already gave the client
    # live source output; the final call gives properly scored + verified results.
    return await find_emails(domain, person_name=person_name, config=cfg)


def _build_sources(cfg: FinderConfig) -> list[Any]:  # BaseSource subclasses
    """Build the source list from a FinderConfig (mirrors finder.py)."""
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
    if cfg.use_intelligent_search:
        from coldreach.sources.intelligent_search import IntelligentSearchSource

        sources.append(
            IntelligentSearchSource(
                searxng_url=cfg.searxng_url or "http://localhost:8088",
                timeout=cfg.request_timeout,
            )
        )
    if cfg.use_harvester:
        sources.append(
            HarvesterSource(
                sources=cfg.harvester_sources,
                timeout=cfg.harvester_max_wait,
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
# Routes — v2 job-based scanning (pub/sub, long-lived SSE)
# ---------------------------------------------------------------------------
# The v2 API solves the core problem: SSE stays open until ALL sources are
# done, delivering emails one-at-a-time as each source finds them.
# SpiderFoot results stream via REST API polling — no blocking docker exec.
# ---------------------------------------------------------------------------


class ScanRequest(BaseModel):
    """Parameters for a v2 streaming scan job."""

    domain: str | None = Field(None, description="Target domain.")
    company: str | None = Field(None, description="Company name — resolved to domain.")
    name: str | None = Field(None, description="Person full name for pattern narrowing.")
    quick: bool = Field(False, description="Skip slow sources.")
    full_scan: bool = Field(False, description="Enable all sources including SpiderFoot.")
    min_confidence: int = Field(0, ge=0, le=100)
    use_firecrawl: bool = Field(False)
    no_cache: bool = Field(False)
    refresh: bool = Field(False)


@app.post("/api/v2/scan")
async def v2_start_scan(req: ScanRequest) -> dict[str, str]:
    """Start a scan job.  Returns job_id immediately.

    Stream results via ``GET /api/v2/scan/{job_id}/stream``.
    Cancel via ``DELETE /api/v2/scan/{job_id}``.
    """
    # Resolve domain
    if req.domain:
        domain = req.domain.strip().lower().removeprefix("www.")
    elif req.company:
        resolved = await resolve_domain(req.company)
        if not resolved:
            raise HTTPException(
                status_code=422,
                detail=f"Could not resolve domain for '{req.company}'.",
            )
        domain = resolved
    else:
        raise HTTPException(status_code=422, detail="Provide 'domain' or 'company'.")

    job_id = secrets.token_urlsafe(10)
    job = ScanJob(job_id=job_id, domain=domain)
    _jobs[job_id] = job

    # Start the scan in the background — results flow into job.queue
    task = asyncio.create_task(_run_v2_scan(job, req))
    task.add_done_callback(lambda t: t.exception() if not t.cancelled() else None)
    job.tasks.append(task)

    return {"job_id": job_id, "domain": domain, "status": "running"}


@app.get("/api/v2/scan/{job_id}/stream")
async def v2_stream(job_id: str) -> StreamingResponse:
    """Stream scan results as Server-Sent Events.

    Stays open until the job completes or is cancelled.

    Event types
    -----------
    ``start``       — ``{ domain, job_id }``
    ``email_found`` — ``{ email, source, confidence, status }`` (one per email)
    ``source_done`` — ``{ source, found, total_so_far }``
    ``complete``    — ``{ total, job_id }``
    ``error``       — ``{ detail }``
    """
    if job_id not in _jobs:
        return StreamingResponse(
            _sse_iter([_sse_event("error", {"detail": f"Job {job_id} not found"})]),
            media_type="text/event-stream",
        )

    return StreamingResponse(
        _drain_job_queue(_jobs[job_id]),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.delete("/api/v2/scan/{job_id}")
async def v2_cancel(job_id: str) -> dict[str, str]:
    """Cancel a running scan job."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    job.cancelled = True
    for t in job.tasks:
        t.cancel()
    await job.queue.put(None)  # signal SSE to close
    return {"job_id": job_id, "status": "cancelled"}


@app.get("/api/v2/scan/{job_id}")
async def v2_status(job_id: str) -> dict[str, Any]:
    """Poll current status + accumulated emails (no SSE needed).

    The extension background SW polls this every 3s to get results
    even if the popup was closed and reopened.
    """
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    running_tasks = [t for t in job.tasks if not t.done()]
    status = "cancelled" if job.cancelled else "complete" if job.done else "running"
    return {
        "job_id": job_id,
        "domain": job.domain,
        "status": status,
        "emails": job.emails,  # All emails found so far
        "sources_done": job.sources_done,
        "total": len(job.emails),
        "running_sources": len(running_tasks),
    }


# ── Job internals ─────────────────────────────────────────────────────────────


async def _drain_job_queue(job: ScanJob) -> AsyncIterator[str]:
    """Drain job queue and yield SSE frames until job completes."""
    yield _sse_event("start", {"domain": job.domain, "job_id": job.job_id})
    while True:
        try:
            item = await asyncio.wait_for(job.queue.get(), timeout=30.0)
        except TimeoutError:
            # Keep-alive ping to prevent proxy timeouts
            yield ": keepalive\n\n"
            continue
        if item is None:
            break
        yield _sse_event(item["_event"], {k: v for k, v in item.items() if k != "_event"})
    yield _sse_event("complete", {"job_id": job.job_id})
    _jobs.pop(job.job_id, None)


async def _sse_iter(frames: list[str]) -> AsyncIterator[str]:
    for f in frames:
        yield f


async def _run_v2_scan(job: ScanJob, req: ScanRequest) -> None:
    """Run all sources, pushing results into job.queue as they arrive."""
    from coldreach.core.finder import _SLOW_SOURCE_NAMES
    from coldreach.sources.spiderfoot import SpiderFootSource

    cfg = _finder_config_v2(req)
    all_sources = _build_sources(cfg)

    # Separate fast vs slow so they don't block each other
    fast_srcs = [s for s in all_sources if s.name not in _SLOW_SOURCE_NAMES]
    slow_srcs = [s for s in all_sources if s.name in _SLOW_SOURCE_NAMES]

    domain = job.domain
    emails_seen: set[str] = set()
    sources_done = 0
    total_sources = len(all_sources)

    async def _run_source(src: BaseSource) -> None:
        nonlocal sources_done
        if job.cancelled:
            return
        try:
            # SpiderFoot gets special streaming treatment
            if isinstance(src, SpiderFootSource):
                found = 0
                async for result in src.fetch_stream(domain):
                    if job.cancelled:
                        break
                    email = result.email.lower()
                    if email not in emails_seen:
                        emails_seen.add(email)
                        found += 1
                        ev = {
                            "_event": "email_found",
                            "email": result.email,
                            "source": result.source.value,
                            "confidence": result.confidence_hint + 30,
                            "status": "unknown",
                        }
                        job.emails.append({k: v for k, v in ev.items() if k != "_event"})
                        await job.queue.put(ev)
            else:
                results, _ = await src.run(domain)
                found = 0
                for result in results:
                    if job.cancelled:
                        break
                    email = result.email.lower()
                    if email not in emails_seen:
                        emails_seen.add(email)
                        found += 1
                        ev = {
                            "_event": "email_found",
                            "email": result.email,
                            "source": result.source.value,
                            "confidence": result.confidence_hint + 30,
                            "status": "unknown",
                        }
                        job.emails.append({k: v for k, v in ev.items() if k != "_event"})
                        await job.queue.put(ev)

            job.sources_done.append(src.name)
            sources_done_local = sources_done + 1
            await job.queue.put(
                {
                    "_event": "source_done",
                    "source": src.name,
                    "found": found,
                    "total_so_far": len(emails_seen),
                    "sources_done": sources_done_local,
                    "sources_total": total_sources,
                    "percent": round(sources_done_local / total_sources * 100),
                }
            )

        except Exception as exc:
            logger.warning("[job %s] source %s error: %s", job.job_id, src.name, exc)
        finally:
            sources_done += 1

    # ── Run fast sources concurrently ────────────────────────────────────────
    await asyncio.gather(*[_run_source(s) for s in fast_srcs])

    # ── Always generate role emails (guaranteed results even if all sources empty)
    # These are pattern candidates: info@, support@, contact@, sales@, etc.
    # They go through Reacher verification when the user verifies them.
    if not job.cancelled:
        from coldreach.generate.patterns import generate_role_emails

        for rp in generate_role_emails(domain):
            if rp.email not in emails_seen:
                emails_seen.add(rp.email)
                ev = {
                    "_event": "email_found",
                    "email": rp.email,
                    "source": "generated/pattern",
                    "confidence": 35,
                    "status": "unknown",
                }
                job.emails.append({k: v for k, v in ev.items() if k != "_event"})
                await job.queue.put(ev)

        logger.info(
            "[job %s] role emails added; total so far: %d",
            job.job_id,
            len(emails_seen),
        )

    # ── Run slow sources (SpiderFoot, theHarvester) ────────────────────────
    if not job.cancelled:
        await asyncio.gather(*[_run_source(s) for s in slow_srcs])

    # ── Signal SSE to close and mark job complete ─────────────────────────
    job.done = True
    await job.queue.put(None)
    logger.info(
        "[job %s] complete — %d emails from %d sources",
        job.job_id,
        len(job.emails),
        len(job.sources_done),
    )


def _finder_config_v2(req: ScanRequest) -> FinderConfig:
    if req.full_scan:
        return FinderConfig(
            use_harvester=True,
            use_spiderfoot=True,
            use_firecrawl=req.use_firecrawl,
            use_cache=not req.no_cache,
            refresh_cache=req.refresh,
            min_confidence=req.min_confidence,
        )
    return FinderConfig(
        use_harvester=not req.quick,
        use_spiderfoot=not req.quick,
        use_firecrawl=req.use_firecrawl,
        use_cache=not req.no_cache,
        refresh_cache=req.refresh,
        min_confidence=req.min_confidence,
    )


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
