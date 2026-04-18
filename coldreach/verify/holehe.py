"""
Holehe platform-presence check.

Uses the holehe library (github.com/megadose/holehe) to check whether an
email address is registered on 120+ public platforms (GitHub, Discord,
Spotify, Slack, etc.).

A positive result on multiple platforms confirms the email is real and the
person is active — especially valuable for catch-all domains where SMTP
verification is unreliable.

IMPORTANT: This check makes up to 120 HTTP requests. It is SLOW (15-45s).
Only enable it explicitly via --holehe or use_holehe=True in FinderConfig.

Score deltas:
  +15  registered on ≥ 2 platforms
  + 5  registered on exactly 1 platform
    0  not found (WARN, not FAIL — private persons may not be on these platforms)
    0  SKIP — holehe not installed
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from coldreach.verify._types import CheckResult

logger = logging.getLogger(__name__)

_MIN_PLATFORMS = 2
_CONCURRENCY = 15


async def check_holehe(
    email: str,
    *,
    timeout: float = 10.0,
    min_platforms: int = _MIN_PLATFORMS,
    concurrency: int = _CONCURRENCY,
) -> CheckResult:
    """Check if *email* is registered on public platforms via holehe.

    Parameters
    ----------
    email:
        Email address to check.
    timeout:
        Per-request HTTP timeout for holehe module calls.
    min_platforms:
        Registrations needed to award the full +15 score delta.
    concurrency:
        Maximum simultaneous holehe module requests.

    Returns
    -------
    CheckResult
        PASS (+15) if registered on ≥ min_platforms platforms.
        PASS (+5) if registered on exactly 1 platform.
        WARN (0) if 0 registrations found.
        SKIP if holehe is not installed.
    """
    try:
        from holehe.core import get_functions, import_submodules
    except ImportError:
        logger.debug("holehe not installed — skipping platform check")
        return CheckResult.skip("holehe not installed")

    modules = import_submodules("holehe.modules")
    websites = get_functions(modules)

    out: list[dict[str, object]] = []
    sem = asyncio.Semaphore(concurrency)

    async def _run(module: Any, client: httpx.AsyncClient) -> None:
        async with sem:
            try:
                await module(email, client, out)
            except Exception as exc:
                logger.debug(
                    "holehe module %s error: %s",
                    getattr(module, "__name__", "?"),
                    exc,
                )

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        await asyncio.gather(*[_run(m, client) for m in websites])

    registered = [r for r in out if r.get("exists")]
    count = len(registered)
    names = [str(r.get("name") or r.get("domain") or "?") for r in registered]

    logger.debug(
        "holehe: %d/%d platforms matched for %s: %s",
        count,
        len(websites),
        email,
        names[:8],
    )

    if count >= min_platforms:
        return CheckResult.pass_(
            f"Registered on {count} platform(s): {', '.join(names[:5])}",
            score_delta=15,
            platforms=names,
            platform_count=count,
        )
    if count >= 1:
        return CheckResult.pass_(
            f"Registered on {count} platform(s): {', '.join(names[:5])}",
            score_delta=5,
            platforms=names,
            platform_count=count,
        )
    return CheckResult.warn(
        "Not found on any checked platforms",
        score_delta=0,
        platforms=[],
        platform_count=0,
    )
