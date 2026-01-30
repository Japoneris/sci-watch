"""
Unified components for sci_watch.

This package contains unified implementations that work across
both HackerNews and arXiv (and potentially other sources).

Modules:
- query: Unified query system for filtering articles
- apis: API clients for fetching from different sources
"""

from . import query
from . import apis

__all__ = ['query', 'apis']
