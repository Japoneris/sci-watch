"""
Loader utilities for query JSON files.

Loads queries from the queries/ folder at the project root.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from .query import Query, QueryCollection


def get_queries_dir() -> Path:
    """Get the path to the queries directory."""
    # Navigate from this file to project root
    current = Path(__file__).resolve()
    project_root = current.parent.parent.parent
    return project_root / "queries"


def load_query_file(filepath: str) -> Query:
    """
    Load a single query from a JSON file.

    Args:
        filepath: Path to the JSON file

    Returns:
        Query instance
    """
    with open(filepath, 'r') as f:
        data = json.load(f)

    return Query(
        name=data.get("name", data.get("id", "Unnamed")),
        description=data.get("description", ""),
        terms=data.get("terms", []),
        categories=data.get("categories", []),
    )


def load_query(query_id: str) -> Query:
    """
    Load a query by its ID from the queries folder.

    Args:
        query_id: The query identifier (filename without .json)

    Returns:
        Query instance

    Raises:
        FileNotFoundError: If query file doesn't exist
    """
    queries_dir = get_queries_dir()
    filepath = queries_dir / f"{query_id}.json"

    if not filepath.exists():
        available = list_query_files()
        raise FileNotFoundError(
            f"Query '{query_id}' not found. Available: {available}"
        )

    return load_query_file(str(filepath))


def list_query_files() -> List[str]:
    """
    List all available query IDs in the queries folder.

    Returns:
        List of query IDs (filenames without .json extension)
    """
    queries_dir = get_queries_dir()
    if not queries_dir.exists():
        return []

    return [
        f.stem for f in queries_dir.glob("*.json")
    ]


def load_all_queries() -> QueryCollection:
    """
    Load all queries from the queries folder.

    Returns:
        QueryCollection with all queries
    """
    collection = QueryCollection()
    queries_dir = get_queries_dir()

    if not queries_dir.exists():
        return collection

    for filepath in queries_dir.glob("*.json"):
        query_id = filepath.stem
        try:
            query = load_query_file(str(filepath))
            collection.add(query_id, query)
        except Exception as e:
            print(f"Warning: Failed to load {filepath}: {e}")

    return collection


def load_queries_by_source(source: str) -> QueryCollection:
    """
    Load queries that originated from a specific source.

    Args:
        source: 'hackernews', 'arxiv', or 'both'

    Returns:
        QueryCollection with matching queries
    """
    collection = QueryCollection()
    queries_dir = get_queries_dir()

    if not queries_dir.exists():
        return collection

    for filepath in queries_dir.glob("*.json"):
        with open(filepath, 'r') as f:
            data = json.load(f)

        if data.get("source") == source:
            query_id = filepath.stem
            query = Query(
                name=data.get("name", query_id),
                description=data.get("description", ""),
                terms=data.get("terms", []),
                categories=data.get("categories", []),
            )
            collection.add(query_id, query)

    return collection


def save_query(query_id: str, query: Query, source: str = "custom") -> str:
    """
    Save a query to the queries folder.

    Args:
        query_id: Identifier for the query (will be filename)
        query: Query instance to save
        source: Source identifier ('hackernews', 'arxiv', 'custom', etc.)

    Returns:
        Path to the saved file
    """
    queries_dir = get_queries_dir()
    queries_dir.mkdir(parents=True, exist_ok=True)

    data = {
        "id": query_id,
        "name": query.name,
        "description": query.description,
        "terms": query.terms,
        "categories": query.categories,
        "source": source,
    }

    filepath = queries_dir / f"{query_id}.json"
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

    return str(filepath)


def delete_query(query_id: str) -> bool:
    """
    Delete a query file.

    Args:
        query_id: Query identifier

    Returns:
        True if deleted, False if not found
    """
    queries_dir = get_queries_dir()
    filepath = queries_dir / f"{query_id}.json"

    if filepath.exists():
        filepath.unlink()
        return True
    return False
