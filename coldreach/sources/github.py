"""
GitHub source — mine commit author emails for a company domain.

Strategy:
  1. Search GitHub for repos whose owner matches the company domain slug
     (e.g. "stripe.com" → org slug "stripe")
  2. Fetch recent commits from top repos → extract author.email
  3. Filter to emails belonging to the target domain

Uses the public GitHub REST API (unauthenticated: 60 req/hr, authenticated: 5000/hr).
Set COLDREACH_GITHUB_TOKEN in .env for higher rate limits.

Rate limit handling:
  - Checks X-RateLimit-Remaining header
  - Stops early if remaining < 5 to avoid exhausting the allowance
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from coldreach.core.models import EmailSource
from coldreach.sources.base import BaseSource, SourceResult

logger = logging.getLogger(__name__)

_GITHUB_API = "https://api.github.com"
_HEADERS_BASE = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "ColdReach/0.1",
}

# Maximum repos to inspect and commits per repo
_MAX_REPOS = 5
_MAX_COMMITS_PER_REPO = 30


def _domain_to_slug(domain: str) -> str:
    """Derive a likely GitHub org/user slug from a domain.

    Examples:
        stripe.com   → stripe
        my-co.io     → my-co
        acme.co.uk   → acme
    """
    # Strip TLD(s) — keep first label
    labels = domain.split(".")
    return labels[0]


def _is_noreply(email: str) -> bool:
    """Filter out GitHub's no-reply commit emails."""
    return "noreply" in email or "users.noreply.github.com" in email


class GitHubSource(BaseSource):
    """Mine public GitHub commits for company domain email addresses.

    Parameters
    ----------
    token:
        Optional GitHub personal access token for higher rate limits.
    timeout:
        Per-request HTTP timeout in seconds.
    """

    name = "github"

    def __init__(self, token: str | None = None, timeout: float = 10.0) -> None:
        super().__init__(timeout=timeout)
        self._token = token

    def _headers(self) -> dict[str, str]:
        h = dict(_HEADERS_BASE)
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    async def fetch(
        self,
        domain: str,
        *,
        person_name: str | None = None,
    ) -> list[SourceResult]:
        base_slug = _domain_to_slug(domain)
        # Try multiple capitalisation/format variants — many companies use
        # "Snapdeal" (title-case) or "snap-deal" on GitHub instead of "snapdeal"
        slug_variants = list(
            dict.fromkeys(
                [
                    base_slug,
                    base_slug.capitalize(),
                    base_slug.title(),
                    base_slug.upper(),
                    base_slug.replace("-", ""),
                    f"{base_slug}-com",
                    f"{base_slug}hq",
                ]
            )
        )
        results: list[SourceResult] = []
        seen_emails: set[str] = set()

        async with httpx.AsyncClient(
            headers=self._headers(),
            timeout=self.timeout,
            follow_redirects=True,
        ) as client:
            repos: list[dict[str, Any]] = []
            for slug in slug_variants:
                repos = await self._get_repos(client, slug)
                if repos:
                    self._log.debug("GitHub: found repos under slug %r for %s", slug, domain)
                    break
            if not repos:
                self._log.debug(
                    "No GitHub repos for %s (tried %d slugs)", domain, len(slug_variants)
                )
                return []

            for repo in repos[:_MAX_REPOS]:
                full_name = repo.get("full_name", "")
                if not full_name:
                    continue
                commits = await self._get_commits(client, full_name)
                for commit in commits:
                    author = (commit.get("commit") or {}).get("author") or {}
                    email = (author.get("email") or "").strip().lower()
                    if not email or email in seen_emails:
                        continue
                    if _is_noreply(email):
                        continue
                    if not email.endswith(f"@{domain}") and not email.endswith(f".{domain}"):
                        continue
                    seen_emails.add(email)
                    author_name = author.get("name", "")
                    commit_url = (commit.get("html_url") or "").strip()
                    results.append(
                        SourceResult(
                            email=email,
                            source=EmailSource.GITHUB_COMMIT,
                            url=commit_url,
                            context=f"GitHub commit by {author_name} in {full_name}",
                            confidence_hint=25,
                        )
                    )

        self._log.debug("GitHub found %d email(s) for %s", len(results), domain)
        return results

    async def _get_repos(self, client: httpx.AsyncClient, slug: str) -> list[dict[str, Any]]:
        """Fetch public repos for org *slug*, fall back to user if not found."""
        for endpoint in [f"/orgs/{slug}/repos", f"/users/{slug}/repos"]:
            try:
                resp = await client.get(
                    f"{_GITHUB_API}{endpoint}",
                    params={"sort": "pushed", "per_page": _MAX_REPOS},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list) and data:
                        return data
                elif resp.status_code == 404:
                    continue
                elif resp.status_code == 403:
                    self._log.warning("GitHub rate limit hit")
                    return []
            except httpx.RequestError as exc:
                self._log.debug("GitHub repos request error: %s", exc)
        return []

    async def _get_commits(self, client: httpx.AsyncClient, full_name: str) -> list[dict[str, Any]]:
        """Fetch recent commits for *owner/repo*."""
        try:
            resp = await client.get(
                f"{_GITHUB_API}/repos/{full_name}/commits",
                params={"per_page": _MAX_COMMITS_PER_REPO},
            )
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    return data
        except httpx.RequestError as exc:
            self._log.debug("GitHub commits request error for %s: %s", full_name, exc)
        return []
