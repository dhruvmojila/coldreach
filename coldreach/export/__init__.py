"""
Result export helpers — write DomainResult to CSV or JSON files.

Exports
-------
export_results
    Write a DomainResult to a file. Format is inferred from the file extension.
"""

from coldreach.export.writer import export_results

__all__ = ["export_results"]
