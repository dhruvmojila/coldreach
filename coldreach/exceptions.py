"""
ColdReach custom exceptions.

Hierarchy
---------
ColdReachError
├── ConfigError           — bad or missing configuration
├── SourceError           — data source (scraper / API) failed
│   └── RateLimitError    — upstream rate limit hit
├── VerificationError     — error during email verification
└── ServiceUnavailableError — a Docker service is not reachable
"""

from __future__ import annotations


class ColdReachError(Exception):
    """Base exception for all ColdReach errors."""


class ConfigError(ColdReachError):
    """Raised when configuration is invalid or missing."""


class SourceError(ColdReachError):
    """Raised when a data source fails to return results."""


class RateLimitError(SourceError):
    """Raised when an upstream service rate-limits the request.

    Attributes
    ----------
    service:
        Human-readable service name (e.g. ``"SearXNG"``).
    retry_after:
        Suggested number of seconds to wait before retrying, if provided
        by the upstream service.
    """

    def __init__(self, service: str, retry_after: int | None = None) -> None:
        self.service = service
        self.retry_after = retry_after
        msg = f"Rate limited by {service}"
        if retry_after is not None:
            msg += f" — retry after {retry_after}s"
        super().__init__(msg)


class VerificationError(ColdReachError):
    """Raised when the verification pipeline encounters an unrecoverable error."""


class ServiceUnavailableError(ColdReachError):
    """Raised when a required Docker service cannot be reached.

    Attributes
    ----------
    service:
        Short service name used in docker-compose.yml (e.g. ``"reacher"``).
    url:
        The URL that was attempted.
    """

    def __init__(self, service: str, url: str) -> None:
        self.service = service
        self.url = url
        super().__init__(
            f"Service '{service}' is not available at {url}.\n"
            f"Start it with:  docker compose up {service}"
        )
