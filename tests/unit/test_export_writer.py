"""
Unit tests for coldreach.export.writer

No network calls — all I/O uses tmp_path (pytest fixture).
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from coldreach.core.models import (
    DomainResult,
    EmailRecord,
    EmailSource,
    SourceRecord,
    VerificationStatus,
)
from coldreach.export.writer import export_results


def _make_result(domain: str = "acme.com") -> DomainResult:
    result = DomainResult(domain=domain, company_name="Acme Corp")
    result.add_email(
        EmailRecord(
            email="john@acme.com",
            confidence=78,
            status=VerificationStatus.VALID,
            sources=[
                SourceRecord(source=EmailSource.WEBSITE_CONTACT, url="https://acme.com/contact")
            ],
            mx_records=["mail.acme.com"],
        )
    )
    result.add_email(
        EmailRecord(
            email="jane@acme.com",
            confidence=45,
            status=VerificationStatus.UNKNOWN,
            sources=[SourceRecord(source=EmailSource.GITHUB_COMMIT, url="")],
            mx_records=["mail.acme.com"],
        )
    )
    return result


class TestExportCSV:
    def test_creates_file(self, tmp_path: Path) -> None:
        out = tmp_path / "leads.csv"
        export_results(_make_result(), out)
        assert out.exists()

    def test_returns_resolved_path(self, tmp_path: Path) -> None:
        out = tmp_path / "leads.csv"
        returned = export_results(_make_result(), out)
        assert returned == out.resolve()

    def test_header_row(self, tmp_path: Path) -> None:
        out = tmp_path / "leads.csv"
        export_results(_make_result(), out)
        with out.open() as fh:
            reader = csv.DictReader(fh)
            assert reader.fieldnames is not None
            assert "email" in reader.fieldnames
            assert "confidence" in reader.fieldnames
            assert "status" in reader.fieldnames
            assert "sources" in reader.fieldnames

    def test_row_count_matches_emails(self, tmp_path: Path) -> None:
        out = tmp_path / "leads.csv"
        export_results(_make_result(), out)
        with out.open() as fh:
            rows = list(csv.DictReader(fh))
        assert len(rows) == 2

    def test_email_values_correct(self, tmp_path: Path) -> None:
        out = tmp_path / "leads.csv"
        export_results(_make_result(), out)
        with out.open() as fh:
            rows = list(csv.DictReader(fh))
        emails = [r["email"] for r in rows]
        assert "john@acme.com" in emails
        assert "jane@acme.com" in emails

    def test_confidence_is_integer_string(self, tmp_path: Path) -> None:
        out = tmp_path / "leads.csv"
        export_results(_make_result(), out)
        with out.open() as fh:
            rows = list(csv.DictReader(fh))
        john = next(r for r in rows if r["email"] == "john@acme.com")
        assert john["confidence"] == "78"

    def test_sources_pipe_separated(self, tmp_path: Path) -> None:
        out = tmp_path / "leads.csv"
        export_results(_make_result(), out)
        with out.open() as fh:
            rows = list(csv.DictReader(fh))
        john = next(r for r in rows if r["email"] == "john@acme.com")
        assert "website/contact" in john["sources"]

    def test_empty_result_writes_header_only(self, tmp_path: Path) -> None:
        empty = DomainResult(domain="empty.com")
        out = tmp_path / "empty.csv"
        export_results(empty, out)
        with out.open() as fh:
            rows = list(csv.DictReader(fh))
        assert rows == []

    def test_overwrites_existing_file(self, tmp_path: Path) -> None:
        out = tmp_path / "leads.csv"
        out.write_text("old content")
        export_results(_make_result(), out)
        content = out.read_text()
        assert "old content" not in content
        assert "email" in content  # header present


class TestExportJSON:
    def test_creates_file(self, tmp_path: Path) -> None:
        out = tmp_path / "leads.json"
        export_results(_make_result(), out)
        assert out.exists()

    def test_returns_resolved_path(self, tmp_path: Path) -> None:
        out = tmp_path / "leads.json"
        returned = export_results(_make_result(), out)
        assert returned == out.resolve()

    def test_valid_json(self, tmp_path: Path) -> None:
        out = tmp_path / "leads.json"
        export_results(_make_result(), out)
        data = json.loads(out.read_text())
        assert isinstance(data, dict)

    def test_schema_keys_present(self, tmp_path: Path) -> None:
        out = tmp_path / "leads.json"
        export_results(_make_result(), out)
        data = json.loads(out.read_text())
        assert "domain" in data
        assert "total" in data
        assert "emails" in data

    def test_domain_value(self, tmp_path: Path) -> None:
        out = tmp_path / "leads.json"
        export_results(_make_result("stripe.com"), out)
        data = json.loads(out.read_text())
        assert data["domain"] == "stripe.com"

    def test_total_matches_email_count(self, tmp_path: Path) -> None:
        out = tmp_path / "leads.json"
        export_results(_make_result(), out)
        data = json.loads(out.read_text())
        assert data["total"] == len(data["emails"])

    def test_email_objects_have_required_fields(self, tmp_path: Path) -> None:
        out = tmp_path / "leads.json"
        export_results(_make_result(), out)
        data = json.loads(out.read_text())
        for email_obj in data["emails"]:
            assert "email" in email_obj
            assert "confidence" in email_obj
            assert "status" in email_obj


class TestExportValidation:
    def test_raises_on_unsupported_extension(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Unsupported output format"):
            export_results(_make_result(), tmp_path / "leads.txt")

    def test_raises_on_no_extension(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Unsupported output format"):
            export_results(_make_result(), tmp_path / "leads")

    def test_accepts_uppercase_csv_extension(self, tmp_path: Path) -> None:
        out = tmp_path / "leads.CSV"
        export_results(_make_result(), out)
        assert out.exists()

    def test_accepts_uppercase_json_extension(self, tmp_path: Path) -> None:
        out = tmp_path / "leads.JSON"
        export_results(_make_result(), out)
        assert out.exists()
