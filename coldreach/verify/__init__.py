"""
ColdReach email verification module.

Public API
----------
    run_basic_pipeline(email)   → PipelineResult   (syntax + disposable + DNS)
    check_syntax(email)         → CheckResult
    check_disposable(email)     → CheckResult
    check_dns(email)            → CheckResult
    is_disposable(email)        → bool
    get_mx_records(domain)      → list[str]

Example
-------
    import asyncio
    from coldreach.verify import run_basic_pipeline

    result = asyncio.run(run_basic_pipeline("john@stripe.com"))
    print(result.score, result.passed)
"""

from coldreach.verify._types import CheckResult, CheckStatus
from coldreach.verify.disposable import check_disposable, is_disposable
from coldreach.verify.dns_check import check_dns, get_mx_records
from coldreach.verify.pipeline import PipelineResult, run_basic_pipeline
from coldreach.verify.syntax import check_syntax

__all__ = [
    "CheckResult",
    "CheckStatus",
    "PipelineResult",
    "check_disposable",
    "check_dns",
    "check_syntax",
    "get_mx_records",
    "is_disposable",
    "run_basic_pipeline",
]
