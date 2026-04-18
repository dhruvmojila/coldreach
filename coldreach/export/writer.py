"""
Export DomainResult to CSV or JSON.

Format is inferred from the output file extension:
    .csv   → comma-separated values, one row per email
    .json  → JSON array matching the --json CLI output schema

Both formats write UTF-8 encoded files.  Existing files are overwritten.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from coldreach.core.models import DomainResult

# CSV column order — also used as the header row.
_CSV_FIELDS = [
    "email",
    "confidence",
    "status",
    "sources",
    "mx_records",
    "is_catch_all",
    "checked_at",
]


def export_results(result: DomainResult, output_path: str | Path) -> Path:
    """Write *result* to *output_path* in CSV or JSON format.

    Format is determined by the file extension (.csv or .json).

    Parameters
    ----------
    result:
        The DomainResult to export.
    output_path:
        Destination file path.  Parent directories must exist.

    Returns
    -------
    Path
        Resolved absolute path of the written file.

    Raises
    ------
    ValueError
        If the file extension is not ``.csv`` or ``.json``.
    OSError
        If the file cannot be written.

    Examples
    --------
    >>> export_results(domain_result, "leads.csv")
    PosixPath('/abs/path/leads.csv')
    """
    path = Path(output_path).expanduser().resolve()
    ext = path.suffix.lower()

    if ext == ".csv":
        _write_csv(result, path)
    elif ext == ".json":
        _write_json(result, path)
    else:
        raise ValueError(f"Unsupported output format {ext!r}. Use .csv or .json")

    return path


def _write_csv(result: DomainResult, path: Path) -> None:
    """Write one row per email to a UTF-8 CSV file."""
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_CSV_FIELDS)
        writer.writeheader()
        for record in result.emails:
            writer.writerow(
                {
                    "email": record.email,
                    "confidence": record.confidence,
                    "status": record.status.value,
                    "sources": "|".join(record.source_names),
                    "mx_records": "|".join(record.mx_records),
                    "is_catch_all": record.is_catch_all_domain,
                    "checked_at": record.checked_at.isoformat(),
                }
            )


def _write_json(result: DomainResult, path: Path) -> None:
    """Write JSON matching the --json CLI schema."""
    payload = {
        "domain": result.domain,
        "company_name": result.company_name,
        "total": len(result.emails),
        "emails": [r.to_dict() for r in result.emails],
    }
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=str)
