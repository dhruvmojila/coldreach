"""
Unit tests for coldreach.api

All external dependencies are mocked — no real network calls, no Docker
services, no database writes.  Tests use httpx.AsyncClient with the FastAPI
ASGI transport so the full request/response cycle runs in-process.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from coldreach import __version__
from coldreach.api import FindRequest, VerifyRequest, _finder_config, _resolve, _sse_event, app
from coldreach.core.models import (
    DomainResult,
    EmailRecord,
    EmailSource,
    SourceRecord,
    VerificationStatus,
)
from coldreach.verify._types import CheckResult, CheckStatus
from coldreach.verify.pipeline import PipelineResult

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def client() -> AsyncClient:
    """Return an httpx AsyncClient wired directly to the FastAPI app."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c  # type: ignore[misc]


def _make_domain_result(domain: str = "acme.com") -> DomainResult:
    """Build a minimal DomainResult for mocking find_emails()."""
    result = DomainResult(domain=domain)
    record = EmailRecord(
        email=f"ceo@{domain}",
        confidence=80,
        status=VerificationStatus.VALID,
        sources=[SourceRecord(source=EmailSource.WEBSITE_CONTACT)],
    )
    result.add_email(record)
    return result


def _make_pipeline_result(email: str = "ceo@acme.com", passed: bool = True) -> PipelineResult:
    """Build a minimal PipelineResult for mocking run_basic_pipeline()."""
    result = PipelineResult(email=email)
    status = CheckStatus.PASS if passed else CheckStatus.FAIL
    result.checks["syntax"] = CheckResult(status=status, reason="ok", score_delta=0)
    result.checks["disposable"] = CheckResult(status=CheckStatus.PASS, reason="ok", score_delta=5)
    result.checks["dns"] = CheckResult(
        status=CheckStatus.PASS,
        reason="MX found",
        score_delta=10,
        metadata={"mx_records": ["mail.acme.com"]},
    )
    return result


# ---------------------------------------------------------------------------
# Root + version
# ---------------------------------------------------------------------------


class TestRootAndVersion:
    @pytest.mark.asyncio
    async def test_root_returns_200(self, client: AsyncClient) -> None:
        resp = await client.get("/")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_root_contains_status_ok(self, client: AsyncClient) -> None:
        resp = await client.get("/")
        assert resp.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_root_contains_version(self, client: AsyncClient) -> None:
        resp = await client.get("/")
        assert resp.json()["version"] == __version__

    @pytest.mark.asyncio
    async def test_root_contains_docs_link(self, client: AsyncClient) -> None:
        resp = await client.get("/")
        assert resp.json()["docs"] == "/docs"

    @pytest.mark.asyncio
    async def test_version_endpoint(self, client: AsyncClient) -> None:
        resp = await client.get("/api/version")
        assert resp.status_code == 200
        assert resp.json() == {"version": __version__}

    @pytest.mark.asyncio
    async def test_swagger_ui_accessible(self, client: AsyncClient) -> None:
        resp = await client.get("/docs")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# POST /api/find — blocking
# ---------------------------------------------------------------------------


class TestFindEndpoint:
    @pytest.mark.asyncio
    async def test_returns_200_with_domain_result(self, client: AsyncClient) -> None:
        mock_result = _make_domain_result()
        with patch("coldreach.api.find_emails", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = mock_result
            resp = await client.post("/api/find", json={"domain": "acme.com"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["domain"] == "acme.com"
        assert isinstance(body["emails"], list)

    @pytest.mark.asyncio
    async def test_returns_emails_in_response(self, client: AsyncClient) -> None:
        mock_result = _make_domain_result()
        with patch("coldreach.api.find_emails", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = mock_result
            resp = await client.post("/api/find", json={"domain": "acme.com"})
        emails = resp.json()["emails"]
        assert len(emails) == 1
        assert emails[0]["email"] == "ceo@acme.com"

    @pytest.mark.asyncio
    async def test_strips_www_prefix_from_domain(self, client: AsyncClient) -> None:
        mock_result = _make_domain_result("acme.com")
        with patch("coldreach.api.find_emails", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = mock_result
            await client.post("/api/find", json={"domain": "www.acme.com"})
        called_domain = mock_find.call_args[0][0]
        assert called_domain == "acme.com"

    @pytest.mark.asyncio
    async def test_resolves_company_to_domain(self, client: AsyncClient) -> None:
        mock_result = _make_domain_result("acme.com")
        with (
            patch("coldreach.api.resolve_domain", new_callable=AsyncMock) as mock_resolve,
            patch("coldreach.api.find_emails", new_callable=AsyncMock) as mock_find,
        ):
            mock_resolve.return_value = "acme.com"
            mock_find.return_value = mock_result
            resp = await client.post("/api/find", json={"company": "Acme Corp"})
        assert resp.status_code == 200
        mock_resolve.assert_awaited_once_with("Acme Corp")

    @pytest.mark.asyncio
    async def test_422_when_company_cannot_be_resolved(self, client: AsyncClient) -> None:
        with patch("coldreach.api.resolve_domain", new_callable=AsyncMock) as mock_resolve:
            mock_resolve.return_value = None
            resp = await client.post("/api/find", json={"company": "UnknownXYZ123"})
        assert resp.status_code == 422
        assert "resolve" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_422_when_no_domain_or_company(self, client: AsyncClient) -> None:
        resp = await client.post("/api/find", json={})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_quick_true_disables_harvester_and_spiderfoot(self, client: AsyncClient) -> None:
        mock_result = _make_domain_result()
        with patch("coldreach.api.find_emails", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = mock_result
            await client.post("/api/find", json={"domain": "acme.com", "quick": True})
        cfg = mock_find.call_args[1]["config"]
        assert cfg.use_harvester is False
        assert cfg.use_spiderfoot is False

    @pytest.mark.asyncio
    async def test_quick_false_enables_harvester_and_spiderfoot(self, client: AsyncClient) -> None:
        mock_result = _make_domain_result()
        with patch("coldreach.api.find_emails", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = mock_result
            await client.post("/api/find", json={"domain": "acme.com", "quick": False})
        cfg = mock_find.call_args[1]["config"]
        assert cfg.use_harvester is True
        assert cfg.use_spiderfoot is True

    @pytest.mark.asyncio
    async def test_min_confidence_passed_to_config(self, client: AsyncClient) -> None:
        mock_result = _make_domain_result()
        with patch("coldreach.api.find_emails", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = mock_result
            await client.post("/api/find", json={"domain": "acme.com", "min_confidence": 50})
        cfg = mock_find.call_args[1]["config"]
        assert cfg.min_confidence == 50

    @pytest.mark.asyncio
    async def test_no_cache_flag_passed_to_config(self, client: AsyncClient) -> None:
        mock_result = _make_domain_result()
        with patch("coldreach.api.find_emails", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = mock_result
            await client.post("/api/find", json={"domain": "acme.com", "no_cache": True})
        cfg = mock_find.call_args[1]["config"]
        assert cfg.use_cache is False

    @pytest.mark.asyncio
    async def test_min_confidence_validation_rejects_over_100(self, client: AsyncClient) -> None:
        resp = await client.post("/api/find", json={"domain": "acme.com", "min_confidence": 101})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_min_confidence_validation_rejects_negative(self, client: AsyncClient) -> None:
        resp = await client.post("/api/find", json={"domain": "acme.com", "min_confidence": -1})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_person_name_forwarded(self, client: AsyncClient) -> None:
        mock_result = _make_domain_result()
        with patch("coldreach.api.find_emails", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = mock_result
            await client.post("/api/find", json={"domain": "acme.com", "name": "Jane Smith"})
        assert mock_find.call_args[1]["person_name"] == "Jane Smith"

    @pytest.mark.asyncio
    async def test_quick_is_true_by_default(self, client: AsyncClient) -> None:
        mock_result = _make_domain_result()
        with patch("coldreach.api.find_emails", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = mock_result
            await client.post("/api/find", json={"domain": "acme.com"})
        cfg = mock_find.call_args[1]["config"]
        # quick=True → harvester and spiderfoot disabled
        assert cfg.use_harvester is False

    @pytest.mark.asyncio
    async def test_response_is_json(self, client: AsyncClient) -> None:
        mock_result = _make_domain_result()
        with patch("coldreach.api.find_emails", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = mock_result
            resp = await client.post("/api/find", json={"domain": "acme.com"})
        assert resp.headers["content-type"].startswith("application/json")


# ---------------------------------------------------------------------------
# POST /api/find/stream — SSE
# ---------------------------------------------------------------------------


class TestFindStreamEndpoint:
    @pytest.mark.asyncio
    async def test_returns_text_event_stream_content_type(self, client: AsyncClient) -> None:
        mock_result = _make_domain_result()
        with patch("coldreach.api.find_emails", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = mock_result
            # Patch _build_sources to return empty list so no real sources run
            with patch("coldreach.api._build_sources", return_value=[]):
                resp = await client.post("/api/find/stream", json={"domain": "acme.com"})
        assert "text/event-stream" in resp.headers["content-type"]

    @pytest.mark.asyncio
    async def test_stream_ends_with_complete_event(self, client: AsyncClient) -> None:
        mock_result = _make_domain_result()
        with patch("coldreach.api.find_emails", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = mock_result
            with patch("coldreach.api._build_sources", return_value=[]):
                resp = await client.post("/api/find/stream", json={"domain": "acme.com"})
        assert "event: complete" in resp.text

    @pytest.mark.asyncio
    async def test_stream_complete_event_contains_domain_result(self, client: AsyncClient) -> None:
        mock_result = _make_domain_result()
        with patch("coldreach.api.find_emails", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = mock_result
            with patch("coldreach.api._build_sources", return_value=[]):
                resp = await client.post("/api/find/stream", json={"domain": "acme.com"})
        # Parse the complete event's data line
        lines = resp.text.splitlines()
        data_lines = [ln for ln in lines if ln.startswith("data:") and "acme.com" in ln]
        assert data_lines, "No complete event data containing domain found"
        payload = json.loads(data_lines[-1][len("data:") :].strip())
        assert payload["domain"] == "acme.com"

    @pytest.mark.asyncio
    async def test_stream_emits_error_event_when_no_domain_or_company(
        self, client: AsyncClient
    ) -> None:
        resp = await client.post("/api/find/stream", json={})
        assert "event: error" in resp.text

    @pytest.mark.asyncio
    async def test_stream_error_event_when_company_unresolvable(self, client: AsyncClient) -> None:
        with patch("coldreach.api.resolve_domain", new_callable=AsyncMock) as mock_resolve:
            mock_resolve.return_value = None
            resp = await client.post("/api/find/stream", json={"company": "UnknownXYZ999"})
        assert "event: error" in resp.text

    @pytest.mark.asyncio
    async def test_stream_has_cache_control_no_cache_header(self, client: AsyncClient) -> None:
        mock_result = _make_domain_result()
        with patch("coldreach.api.find_emails", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = mock_result
            with patch("coldreach.api._build_sources", return_value=[]):
                resp = await client.post("/api/find/stream", json={"domain": "acme.com"})
        assert resp.headers.get("cache-control") == "no-cache"


# ---------------------------------------------------------------------------
# POST /api/verify
# ---------------------------------------------------------------------------


class TestVerifyEndpoint:
    @pytest.mark.asyncio
    async def test_returns_200_for_valid_email(self, client: AsyncClient) -> None:
        mock_pipeline = _make_pipeline_result(passed=True)
        with patch("coldreach.api.run_basic_pipeline", new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = mock_pipeline
            resp = await client.post("/api/verify", json={"email": "ceo@acme.com"})
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_response_contains_passed_field(self, client: AsyncClient) -> None:
        mock_pipeline = _make_pipeline_result(passed=True)
        with patch("coldreach.api.run_basic_pipeline", new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = mock_pipeline
            resp = await client.post("/api/verify", json={"email": "ceo@acme.com"})
        body = resp.json()
        assert "passed" in body

    @pytest.mark.asyncio
    async def test_response_contains_score(self, client: AsyncClient) -> None:
        mock_pipeline = _make_pipeline_result(passed=True)
        with patch("coldreach.api.run_basic_pipeline", new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = mock_pipeline
            resp = await client.post("/api/verify", json={"email": "ceo@acme.com"})
        body = resp.json()
        assert "score" in body
        assert isinstance(body["score"], int)

    @pytest.mark.asyncio
    async def test_response_contains_checks(self, client: AsyncClient) -> None:
        mock_pipeline = _make_pipeline_result(passed=True)
        with patch("coldreach.api.run_basic_pipeline", new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = mock_pipeline
            resp = await client.post("/api/verify", json={"email": "ceo@acme.com"})
        body = resp.json()
        assert "checks" in body
        assert "syntax" in body["checks"]

    @pytest.mark.asyncio
    async def test_email_forwarded_to_pipeline(self, client: AsyncClient) -> None:
        mock_pipeline = _make_pipeline_result()
        with patch("coldreach.api.run_basic_pipeline", new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = mock_pipeline
            await client.post("/api/verify", json={"email": "jane@example.com"})
        assert mock_verify.call_args[0][0] == "jane@example.com"

    @pytest.mark.asyncio
    async def test_run_holehe_forwarded_to_pipeline(self, client: AsyncClient) -> None:
        mock_pipeline = _make_pipeline_result()
        with patch("coldreach.api.run_basic_pipeline", new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = mock_pipeline
            await client.post("/api/verify", json={"email": "jane@example.com", "run_holehe": True})
        assert mock_verify.call_args[1]["run_holehe"] is True

    @pytest.mark.asyncio
    async def test_run_holehe_defaults_to_false(self, client: AsyncClient) -> None:
        mock_pipeline = _make_pipeline_result()
        with patch("coldreach.api.run_basic_pipeline", new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = mock_pipeline
            await client.post("/api/verify", json={"email": "jane@example.com"})
        assert mock_verify.call_args[1]["run_holehe"] is False

    @pytest.mark.asyncio
    async def test_missing_email_returns_422(self, client: AsyncClient) -> None:
        resp = await client.post("/api/verify", json={})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/status
# ---------------------------------------------------------------------------


class TestStatusEndpoint:
    def _make_service(self, name: str, online: bool = True, separate_stack: bool = False) -> Any:
        from coldreach.diagnostics import ServiceResult

        return ServiceResult(
            name=name,
            url="http://localhost:8080",
            role="test service",
            separate_stack=separate_stack,
            online=online,
            latency_ms=42 if online else None,
            detail="HTTP 200" if online else "connection refused",
        )

    def _make_package(self, name: str, installed: bool = True) -> Any:
        from coldreach.diagnostics import PackageResult

        return PackageResult(
            name=name,
            import_name=name,
            install_hint=f"pip install {name}",
            installed=installed,
            version="1.0.0" if installed else "",
        )

    @pytest.mark.asyncio
    async def test_returns_200(self, client: AsyncClient) -> None:
        from coldreach.diagnostics import DiagnosticsReport

        report = DiagnosticsReport(
            services=[self._make_service("SearXNG")],
            packages=[self._make_package("holehe")],
        )
        with patch("coldreach.diagnostics.run", new_callable=AsyncMock, return_value=report):
            resp = await client.get("/api/status")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_response_contains_services(self, client: AsyncClient) -> None:
        from coldreach.diagnostics import DiagnosticsReport

        report = DiagnosticsReport(
            services=[self._make_service("SearXNG", online=True)],
            packages=[],
        )
        with patch("coldreach.diagnostics.run", new_callable=AsyncMock, return_value=report):
            resp = await client.get("/api/status")
        body = resp.json()
        assert "services" in body
        assert len(body["services"]) == 1
        assert body["services"][0]["name"] == "SearXNG"
        assert body["services"][0]["online"] is True

    @pytest.mark.asyncio
    async def test_response_contains_summary(self, client: AsyncClient) -> None:
        from coldreach.diagnostics import DiagnosticsReport

        report = DiagnosticsReport(
            services=[
                self._make_service("SearXNG", online=True),
                self._make_service("Reacher", online=False),
            ],
            packages=[self._make_package("holehe", installed=False)],
        )
        with patch("coldreach.diagnostics.run", new_callable=AsyncMock, return_value=report):
            resp = await client.get("/api/status")
        summary = resp.json()["summary"]
        assert summary["services_online"] == 1
        assert summary["packages_installed"] == 0

    @pytest.mark.asyncio
    async def test_separate_stack_flag_included(self, client: AsyncClient) -> None:
        from coldreach.diagnostics import DiagnosticsReport

        report = DiagnosticsReport(
            services=[self._make_service("Firecrawl", separate_stack=True)],
            packages=[],
        )
        with patch("coldreach.diagnostics.run", new_callable=AsyncMock, return_value=report):
            resp = await client.get("/api/status")
        svc = resp.json()["services"][0]
        assert svc["separate_stack"] is True


# ---------------------------------------------------------------------------
# GET /api/cache  +  DELETE /api/cache/{domain}
# ---------------------------------------------------------------------------


class TestCacheEndpoints:
    @pytest.mark.asyncio
    async def test_cache_list_returns_200(self, client: AsyncClient) -> None:
        with patch("coldreach.api.CacheStore") as mock_store_cls:
            mock_store = MagicMock()
            mock_store.list_domains.return_value = []
            mock_store_cls.return_value = mock_store
            resp = await client.get("/api/cache")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_cache_list_returns_domains(self, client: AsyncClient) -> None:
        cached_at = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC).replace(tzinfo=None)
        rows = [("stripe.com", cached_at, False), ("acme.com", cached_at, True)]
        with patch("coldreach.api.CacheStore") as mock_store_cls:
            mock_store = MagicMock()
            mock_store.list_domains.return_value = rows
            mock_store_cls.return_value = mock_store
            resp = await client.get("/api/cache")
        body = resp.json()
        assert body["total"] == 2
        domains = [d["domain"] for d in body["domains"]]
        assert "stripe.com" in domains
        assert "acme.com" in domains

    @pytest.mark.asyncio
    async def test_cache_list_expired_flag(self, client: AsyncClient) -> None:
        cached_at = datetime(2024, 1, 1, 0, 0, 0)
        with patch("coldreach.api.CacheStore") as mock_store_cls:
            mock_store = MagicMock()
            mock_store.list_domains.return_value = [("old.com", cached_at, True)]
            mock_store_cls.return_value = mock_store
            resp = await client.get("/api/cache")
        domain = resp.json()["domains"][0]
        assert domain["expired"] is True

    @pytest.mark.asyncio
    async def test_cache_list_empty(self, client: AsyncClient) -> None:
        with patch("coldreach.api.CacheStore") as mock_store_cls:
            mock_store = MagicMock()
            mock_store.list_domains.return_value = []
            mock_store_cls.return_value = mock_store
            resp = await client.get("/api/cache")
        body = resp.json()
        assert body["total"] == 0
        assert body["domains"] == []

    @pytest.mark.asyncio
    async def test_cache_clear_returns_success(self, client: AsyncClient) -> None:
        with patch("coldreach.api.CacheStore") as mock_store_cls:
            mock_store = MagicMock()
            mock_store_cls.return_value = mock_store
            resp = await client.delete("/api/cache/stripe.com")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["domain"] == "stripe.com"

    @pytest.mark.asyncio
    async def test_cache_clear_calls_store_clear(self, client: AsyncClient) -> None:
        with patch("coldreach.api.CacheStore") as mock_store_cls:
            mock_store = MagicMock()
            mock_store_cls.return_value = mock_store
            await client.delete("/api/cache/acme.com")
        mock_store.clear.assert_called_once_with(domain="acme.com")


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------


class TestCORS:
    @pytest.mark.asyncio
    async def test_cors_allows_localhost_origin(self, client: AsyncClient) -> None:
        resp = await client.options(
            "/api/version",
            headers={
                "Origin": "http://localhost",
                "Access-Control-Request-Method": "GET",
            },
        )
        # FastAPI returns 200 for OPTIONS with CORS middleware
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_cors_allows_chrome_extension_origin(self, client: AsyncClient) -> None:
        mock_result = _make_domain_result()
        with patch("coldreach.api.find_emails", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = mock_result
            resp = await client.post(
                "/api/find",
                json={"domain": "acme.com"},
                headers={"Origin": "chrome-extension://abcdefghijklmnop"},
            )
        # Should not be blocked — extension origin is whitelisted
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_cors_allows_127_0_0_1_origin(self, client: AsyncClient) -> None:
        resp = await client.get(
            "/api/version",
            headers={"Origin": "http://127.0.0.1"},
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Unit tests for helper functions
# ---------------------------------------------------------------------------


class TestSseEvent:
    def test_format_contains_event_type(self) -> None:
        frame = _sse_event("progress", {"found": 3})
        assert frame.startswith("event: progress\n")

    def test_format_contains_data_line(self) -> None:
        frame = _sse_event("progress", {"found": 3})
        assert "data: " in frame

    def test_format_ends_with_double_newline(self) -> None:
        frame = _sse_event("complete", {"domain": "acme.com"})
        assert frame.endswith("\n\n")

    def test_data_is_valid_json(self) -> None:
        payload = {"source": "github", "found": 2}
        frame = _sse_event("progress", payload)
        data_line = next(ln for ln in frame.splitlines() if ln.startswith("data:"))
        parsed = json.loads(data_line[len("data:") :].strip())
        assert parsed == payload

    def test_serialises_non_json_types_via_default_str(self) -> None:
        from datetime import datetime

        frame = _sse_event("test", {"ts": datetime(2024, 1, 1)})
        # Should not raise — default=str handles datetime
        data_line = next(ln for ln in frame.splitlines() if ln.startswith("data:"))
        assert "2024" in data_line


class TestFinderConfig:
    def test_quick_true_disables_harvester(self) -> None:
        req = FindRequest(domain="acme.com", quick=True)
        cfg = _finder_config(req)
        assert cfg.use_harvester is False
        assert cfg.use_spiderfoot is False

    def test_quick_false_enables_harvester(self) -> None:
        req = FindRequest(domain="acme.com", quick=False)
        cfg = _finder_config(req)
        assert cfg.use_harvester is True
        assert cfg.use_spiderfoot is True

    def test_no_cache_disables_cache(self) -> None:
        req = FindRequest(domain="acme.com", no_cache=True)
        cfg = _finder_config(req)
        assert cfg.use_cache is False

    def test_refresh_flag_forwarded(self) -> None:
        req = FindRequest(domain="acme.com", refresh=True)
        cfg = _finder_config(req)
        assert cfg.refresh_cache is True

    def test_firecrawl_flag_forwarded(self) -> None:
        req = FindRequest(domain="acme.com", use_firecrawl=True)
        cfg = _finder_config(req)
        assert cfg.use_firecrawl is True

    def test_crawl4ai_flag_forwarded(self) -> None:
        req = FindRequest(domain="acme.com", use_crawl4ai=True)
        cfg = _finder_config(req)
        assert cfg.use_crawl4ai is True

    def test_min_confidence_forwarded(self) -> None:
        req = FindRequest(domain="acme.com", min_confidence=60)
        cfg = _finder_config(req)
        assert cfg.min_confidence == 60

    def test_defaults_are_sensible(self) -> None:
        req = FindRequest(domain="acme.com")
        assert req.quick is True
        assert req.min_confidence == 0
        assert req.use_firecrawl is False
        assert req.use_crawl4ai is False
        assert req.no_cache is False
        assert req.refresh is False


class TestResolveHelper:
    @pytest.mark.asyncio
    async def test_returns_domain_when_provided(self) -> None:
        req = FindRequest(domain="Stripe.com")
        result = await _resolve(req)
        assert result == "stripe.com"

    @pytest.mark.asyncio
    async def test_strips_www_prefix(self) -> None:
        req = FindRequest(domain="www.stripe.com")
        result = await _resolve(req)
        assert result == "stripe.com"

    @pytest.mark.asyncio
    async def test_lowercases_domain(self) -> None:
        req = FindRequest(domain="STRIPE.COM")
        result = await _resolve(req)
        assert result == "stripe.com"

    @pytest.mark.asyncio
    async def test_resolves_company_name(self) -> None:
        req = FindRequest(company="Stripe")
        with patch("coldreach.api.resolve_domain", new_callable=AsyncMock) as mock_resolve:
            mock_resolve.return_value = "stripe.com"
            result = await _resolve(req)
        assert result == "stripe.com"
        mock_resolve.assert_awaited_once_with("Stripe")

    @pytest.mark.asyncio
    async def test_raises_422_when_company_unresolvable(self) -> None:
        from fastapi import HTTPException

        req = FindRequest(company="UnknownXYZ")
        with patch("coldreach.api.resolve_domain", new_callable=AsyncMock) as mock_resolve:
            mock_resolve.return_value = None
            with pytest.raises(HTTPException) as exc_info:
                await _resolve(req)
        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_raises_422_when_neither_provided(self) -> None:
        from fastapi import HTTPException

        req = FindRequest()
        with pytest.raises(HTTPException) as exc_info:
            await _resolve(req)
        assert exc_info.value.status_code == 422


# ---------------------------------------------------------------------------
# Request model validation
# ---------------------------------------------------------------------------


class TestFindRequestModel:
    def test_min_confidence_accepts_zero(self) -> None:
        req = FindRequest(domain="acme.com", min_confidence=0)
        assert req.min_confidence == 0

    def test_min_confidence_accepts_100(self) -> None:
        req = FindRequest(domain="acme.com", min_confidence=100)
        assert req.min_confidence == 100

    def test_min_confidence_rejects_negative(self) -> None:
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            FindRequest(domain="acme.com", min_confidence=-1)

    def test_min_confidence_rejects_over_100(self) -> None:
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            FindRequest(domain="acme.com", min_confidence=101)

    def test_domain_and_company_both_none_is_valid_model(self) -> None:
        # Model itself is valid; the 422 comes from the route handler
        req = FindRequest()
        assert req.domain is None
        assert req.company is None


class TestVerifyRequestModel:
    def test_email_required(self) -> None:
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            VerifyRequest()  # type: ignore[call-arg]

    def test_run_holehe_defaults_false(self) -> None:
        req = VerifyRequest(email="ceo@acme.com")
        assert req.run_holehe is False
