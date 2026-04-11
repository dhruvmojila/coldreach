"""
ColdReach — open-source email finder and lead discovery tool.

The free, local alternative to Hunter.io and Apollo.io.
All data stays on your machine. No paid API keys required.

Quick start
-----------
>>> from coldreach import __version__
>>> print(__version__)
0.1.0

CLI usage
---------
    coldreach verify john@acme.com
    coldreach find --domain acme.com
    coldreach find --company "Acme Corp"
"""

from __future__ import annotations

__version__ = "0.1.0"
__author__ = "ColdReach Contributors"
__license__ = "MIT"

__all__ = ["__author__", "__license__", "__version__"]
