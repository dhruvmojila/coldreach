"""
Company-to-domain resolution.

Exports
-------
resolve_domain
    Resolve a company name (e.g. "Stripe") to its primary domain ("stripe.com").
"""

from coldreach.resolve.company import resolve_domain

__all__ = ["resolve_domain"]
