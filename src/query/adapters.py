"""
Platform-specific adapters for the unified query system.

Each adapter knows how to:
1. Apply a unified Query to items from its platform
2. Translate a Query to the platform's native query format (where applicable)
"""

from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

from .query import Query


class BaseAdapter(ABC):
    """Base class for platform adapters."""

    # Default fields to search when filtering
    default_text_fields: List[str] = []

    @abstractmethod
    def filter(
        self,
        items: List[Dict[str, Any]],
        query: Query,
        text_fields: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Filter items using the query.

        Args:
            items: List of items from this platform
            query: Unified query to apply
            text_fields: Fields to search (uses defaults if not provided)

        Returns:
            List of matching items
        """
        pass

    def to_native_query(self, query: Query) -> str:
        """
        Convert unified query to platform's native query string.

        Args:
            query: Unified query

        Returns:
            Native query string for API calls
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support native query conversion"
        )


class HackerNewsAdapter(BaseAdapter):
    """
    Adapter for HackerNews articles.

    Filters articles locally using the boolean expression engine.
    HackerNews API uses Algolia which has its own search, but we
    apply our boolean filters on top of fetched results.
    """

    default_text_fields = ['title', 'story_text']

    def filter(
        self,
        items: List[Dict[str, Any]],
        query: Query,
        text_fields: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Filter HackerNews articles using the query.

        Args:
            items: List of HN article dictionaries
            query: Unified query to apply
            text_fields: Fields to search (default: title, story_text)

        Returns:
            List of matching articles
        """
        if text_fields is None:
            text_fields = self.default_text_fields

        matching = []
        for item in items:
            combined_text = ' '.join(
                str(item.get(field, '') or '')
                for field in text_fields
            )
            if query.matches(combined_text):
                matching.append(item)
        return matching

    def filter_with_matches(
        self,
        items: List[Dict[str, Any]],
        query: Query,
        text_fields: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Filter articles and annotate with matching terms.

        Args:
            items: List of HN article dictionaries
            query: Unified query to apply
            text_fields: Fields to search

        Returns:
            List of matching articles with '_matched_terms' field added
        """
        if text_fields is None:
            text_fields = self.default_text_fields

        matching = []
        for item in items:
            combined_text = ' '.join(
                str(item.get(field, '') or '')
                for field in text_fields
            )
            matched_terms = query.get_matching_terms(combined_text)
            if matched_terms:
                item_copy = item.copy()
                item_copy['_matched_terms'] = matched_terms
                matching.append(item_copy)
        return matching


class ArxivAdapter(BaseAdapter):
    """
    Adapter for arXiv papers.

    Can filter papers locally OR generate native arXiv API query strings.
    """

    default_text_fields = ['title', 'summary']

    def filter(
        self,
        items: List[Dict[str, Any]],
        query: Query,
        text_fields: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Filter arXiv papers locally using the query.

        Args:
            items: List of arXiv paper dictionaries
            query: Unified query to apply
            text_fields: Fields to search (default: title, summary)

        Returns:
            List of matching papers
        """
        if text_fields is None:
            text_fields = self.default_text_fields

        matching = []
        for item in items:
            combined_text = ' '.join(
                str(item.get(field, '') or '')
                for field in text_fields
            )
            if query.matches(combined_text):
                # Optionally filter by categories if specified
                if query.categories:
                    item_cats = item.get('categories', [])
                    if isinstance(item_cats, str):
                        item_cats = [c.strip() for c in item_cats.split(',')]
                    # Check if any category matches
                    if not any(cat in item_cats for cat in query.categories):
                        continue
                matching.append(item)
        return matching

    def filter_with_matches(
        self,
        items: List[Dict[str, Any]],
        query: Query,
        text_fields: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Filter papers and annotate with matching terms.

        Args:
            items: List of arXiv paper dictionaries
            query: Unified query to apply
            text_fields: Fields to search

        Returns:
            List of matching papers with '_matched_terms' field added
        """
        if text_fields is None:
            text_fields = self.default_text_fields

        matching = []
        for item in items:
            combined_text = ' '.join(
                str(item.get(field, '') or '')
                for field in text_fields
            )
            matched_terms = query.get_matching_terms(combined_text)
            if matched_terms:
                # Optionally filter by categories if specified
                if query.categories:
                    item_cats = item.get('categories', [])
                    if isinstance(item_cats, str):
                        item_cats = [c.strip() for c in item_cats.split(',')]
                    if not any(cat in item_cats for cat in query.categories):
                        continue
                item_copy = item.copy()
                item_copy['_matched_terms'] = matched_terms
                matching.append(item_copy)
        return matching

    def to_native_query(self, query: Query) -> str:
        """
        Convert unified query to arXiv API query string.

        The arXiv API uses a specific query syntax. This method converts
        our boolean expressions to that format.

        Args:
            query: Unified query

        Returns:
            arXiv API query string
        """
        if not query.terms:
            return ""

        # Build terms part - combine with OR
        # arXiv expects: ti:"term" for title, abs:"term" for abstract
        # We search in all fields by default
        term_parts = []
        for term in query.terms:
            # Wrap each term - arXiv will search in all fields
            term_parts.append(f"({term})")

        terms_query = " OR ".join(term_parts)

        # Build categories part if specified
        if query.categories:
            cat_parts = [f"cat:{cat}" for cat in query.categories]
            cat_query = " OR ".join(cat_parts)
            return f"({terms_query}) AND ({cat_query})"

        return terms_query


class GenericAdapter(BaseAdapter):
    """
    Generic adapter for any text-based items.

    Use this when you have items that don't fit HackerNews or arXiv format.
    """

    default_text_fields = ['text', 'content', 'title', 'body']

    def __init__(self, text_fields: Optional[List[str]] = None):
        """
        Initialize with custom text fields.

        Args:
            text_fields: Fields to search by default
        """
        if text_fields:
            self.default_text_fields = text_fields

    def filter(
        self,
        items: List[Dict[str, Any]],
        query: Query,
        text_fields: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Filter items using the query.

        Args:
            items: List of item dictionaries
            query: Unified query to apply
            text_fields: Fields to search

        Returns:
            List of matching items
        """
        if text_fields is None:
            text_fields = self.default_text_fields

        matching = []
        for item in items:
            combined_text = ' '.join(
                str(item.get(field, '') or '')
                for field in text_fields
                if field in item
            )
            if combined_text and query.matches(combined_text):
                matching.append(item)
        return matching


# Convenience functions

def get_adapter(platform: str) -> BaseAdapter:
    """
    Get the appropriate adapter for a platform.

    Args:
        platform: Platform name ('hackernews', 'arxiv', or 'generic')

    Returns:
        Adapter instance
    """
    adapters = {
        'hackernews': HackerNewsAdapter,
        'hn': HackerNewsAdapter,
        'arxiv': ArxivAdapter,
        'generic': GenericAdapter,
    }

    adapter_class = adapters.get(platform.lower())
    if adapter_class is None:
        raise ValueError(f"Unknown platform: {platform}. "
                        f"Available: {list(adapters.keys())}")

    return adapter_class()


def filter_items(
    items: List[Dict[str, Any]],
    query: Query,
    platform: str,
    text_fields: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Filter items using the appropriate adapter.

    Args:
        items: List of items to filter
        query: Unified query to apply
        platform: Platform name
        text_fields: Optional custom text fields

    Returns:
        List of matching items
    """
    adapter = get_adapter(platform)
    return adapter.filter(items, query, text_fields)
