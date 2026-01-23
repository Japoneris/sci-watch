"""
Unified Query class for filtering articles from any source.

A Query represents a set of boolean filter expressions that can be
applied to articles from HackerNews, arXiv, or any other text source.
"""

import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path

from .filter_engine import parse_expression, FilterNode


@dataclass
class Query:
    """
    Unified query configuration for filtering articles.

    Attributes:
        name: Human-readable name for this query
        description: Description of what this query matches
        terms: List of boolean filter expressions (combined with OR)
        categories: Optional list of categories (used by arXiv adapter)
    """
    name: str
    description: str = ""
    terms: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)

    _compiled_terms: List[FilterNode] = field(default_factory=list, repr=False)

    def __post_init__(self):
        """Compile terms after initialization."""
        self._compile_terms()

    def _compile_terms(self):
        """Compile all filter terms into AST nodes."""
        self._compiled_terms = []
        for term in self.terms:
            try:
                node = parse_expression(term)
                if node:
                    self._compiled_terms.append(node)
            except SyntaxError as e:
                print(f"Warning: Failed to parse filter term '{term}': {e}")

    def add_term(self, term: str) -> bool:
        """
        Add a new term to the query.

        Args:
            term: Boolean filter expression to add

        Returns:
            True if term was added successfully, False if parsing failed
        """
        try:
            node = parse_expression(term)
            if node:
                self.terms.append(term)
                self._compiled_terms.append(node)
                return True
        except SyntaxError as e:
            print(f"Warning: Failed to parse filter term '{term}': {e}")
        return False

    def remove_term(self, term: str) -> bool:
        """
        Remove a term from the query.

        Args:
            term: Term to remove

        Returns:
            True if term was found and removed
        """
        if term in self.terms:
            idx = self.terms.index(term)
            self.terms.pop(idx)
            if idx < len(self._compiled_terms):
                self._compiled_terms.pop(idx)
            return True
        return False

    def matches(self, text: str) -> bool:
        """
        Check if text matches any of the filter terms.

        Terms are combined with OR - any matching term returns True.

        Args:
            text: Text to check (e.g., title + content)

        Returns:
            True if any filter term matches
        """
        if not text:
            return False

        for node in self._compiled_terms:
            if node.evaluate(text):
                return True
        return False

    def get_matching_terms(self, text: str) -> List[str]:
        """
        Get list of filter terms that match the text.

        Args:
            text: Text to check

        Returns:
            List of matching filter term strings
        """
        matching = []
        for i, node in enumerate(self._compiled_terms):
            if node.evaluate(text):
                matching.append(self.terms[i])
        return matching

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert query to dictionary for serialization.

        Returns:
            Dictionary representation of the query
        """
        result = {
            "name": self.name,
            "description": self.description,
            "terms": self.terms,
        }
        if self.categories:
            result["categories"] = self.categories
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Query":
        """
        Create a Query from a dictionary.

        Args:
            data: Dictionary with query configuration

        Returns:
            Query instance
        """
        return cls(
            name=data.get("name", "Unnamed Query"),
            description=data.get("description", ""),
            terms=data.get("terms", []),
            categories=data.get("categories", []),
        )

    def to_json(self) -> str:
        """Convert query to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "Query":
        """Create a Query from JSON string."""
        return cls.from_dict(json.loads(json_str))


class QueryCollection:
    """
    A collection of named queries.

    Provides methods for managing, saving, and loading query configurations.
    """

    def __init__(self, queries: Optional[Dict[str, Query]] = None):
        """
        Initialize the collection.

        Args:
            queries: Optional dictionary of queries keyed by ID
        """
        self.queries: Dict[str, Query] = queries or {}

    def add(self, query_id: str, query: Query):
        """Add a query to the collection."""
        self.queries[query_id] = query

    def get(self, query_id: str) -> Optional[Query]:
        """Get a query by ID."""
        return self.queries.get(query_id)

    def remove(self, query_id: str) -> bool:
        """Remove a query by ID. Returns True if found and removed."""
        if query_id in self.queries:
            del self.queries[query_id]
            return True
        return False

    def list_ids(self) -> List[str]:
        """Get list of all query IDs."""
        return list(self.queries.keys())

    def __iter__(self):
        """Iterate over (query_id, query) pairs."""
        return iter(self.queries.items())

    def __len__(self):
        return len(self.queries)

    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        """Convert collection to dictionary."""
        return {qid: q.to_dict() for qid, q in self.queries.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Dict[str, Any]]) -> "QueryCollection":
        """Create collection from dictionary."""
        queries = {qid: Query.from_dict(qdata) for qid, qdata in data.items()}
        return cls(queries)

    def save(self, filepath: str):
        """Save collection to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, filepath: str) -> "QueryCollection":
        """Load collection from JSON file."""
        with open(filepath, 'r') as f:
            return cls.from_dict(json.load(f))


def filter_items(
    items: List[Dict[str, Any]],
    query: Query,
    text_fields: List[str],
) -> List[Dict[str, Any]]:
    """
    Filter a list of items using a query.

    Args:
        items: List of item dictionaries
        query: Query to apply
        text_fields: Fields to combine for text matching

    Returns:
        List of items that match the query
    """
    matching = []
    for item in items:
        combined_text = ' '.join(
            str(item.get(field, ''))
            for field in text_fields
        )
        if query.matches(combined_text):
            matching.append(item)
    return matching


def classify_items(
    items: List[Dict[str, Any]],
    queries: QueryCollection,
    text_fields: List[str],
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Classify items into categories based on multiple queries.

    Args:
        items: List of item dictionaries
        queries: Collection of queries
        text_fields: Fields to combine for text matching

    Returns:
        Dictionary mapping query IDs to lists of matching items
    """
    results = {}
    for query_id, query in queries:
        results[query_id] = filter_items(items, query, text_fields)
    return results
