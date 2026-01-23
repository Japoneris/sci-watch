"""
Migration utilities to convert existing configs to unified format.

Use these functions to migrate from:
- HackerNewsTracking/src_select/filter_config.py
- Arxiv_monitoring/config.py
"""

from typing import Dict, Any
from .query import Query, QueryCollection


def from_hackernews_config(filter_configs: Dict[str, Dict[str, Any]]) -> QueryCollection:
    """
    Convert HackerNews filter configs to unified QueryCollection.

    The HN config format:
    {
        "filter_id": {
            "name": "Filter Name",
            "description": "Description",
            "terms": ["term1", "term2", ...]
        }
    }

    Args:
        filter_configs: HackerNews FILTER_CONFIGS dictionary

    Returns:
        Unified QueryCollection
    """
    collection = QueryCollection()

    for filter_id, config in filter_configs.items():
        query = Query(
            name=config.get("name", filter_id),
            description=config.get("description", ""),
            terms=config.get("terms", []),
            categories=[],  # HN doesn't use categories
        )
        collection.add(filter_id, query)

    return collection


def from_arxiv_config(query_configs: Dict[str, Dict[str, Any]]) -> QueryCollection:
    """
    Convert arXiv query configs to unified QueryCollection.

    The arXiv config format:
    {
        "query_id": {
            "name": "Query Name",
            "description": "Description",
            "terms": ["term1", "term2", ...],
            "categories": ["cs.AI", "cs.CL", ...]
        }
    }

    Args:
        query_configs: arXiv QUERY_CONFIGS dictionary

    Returns:
        Unified QueryCollection
    """
    collection = QueryCollection()

    for query_id, config in query_configs.items():
        query = Query(
            name=config.get("name", query_id),
            description=config.get("description", ""),
            terms=config.get("terms", []),
            categories=config.get("categories", []),
        )
        collection.add(query_id, query)

    return collection


def merge_collections(*collections: QueryCollection) -> QueryCollection:
    """
    Merge multiple QueryCollections into one.

    If the same query_id exists in multiple collections,
    later collections will overwrite earlier ones.

    Args:
        *collections: QueryCollections to merge

    Returns:
        Merged QueryCollection
    """
    merged = QueryCollection()
    for collection in collections:
        for query_id, query in collection:
            merged.add(query_id, query)
    return merged


def migrate_existing_configs(
    hn_config_path: str = None,
    arxiv_config_path: str = None,
    output_path: str = None,
) -> QueryCollection:
    """
    Migrate existing config files to unified format.

    Args:
        hn_config_path: Path to HN filter_config.py (imports FILTER_CONFIGS)
        arxiv_config_path: Path to arXiv config.py (imports QUERY_CONFIGS)
        output_path: Optional path to save merged collection as JSON

    Returns:
        Merged QueryCollection
    """
    import importlib.util
    import sys

    collections = []

    if hn_config_path:
        spec = importlib.util.spec_from_file_location("hn_config", hn_config_path)
        hn_module = importlib.util.module_from_spec(spec)
        sys.modules["hn_config"] = hn_module
        spec.loader.exec_module(hn_module)

        if hasattr(hn_module, 'FILTER_CONFIGS'):
            collections.append(from_hackernews_config(hn_module.FILTER_CONFIGS))

    if arxiv_config_path:
        spec = importlib.util.spec_from_file_location("arxiv_config", arxiv_config_path)
        arxiv_module = importlib.util.module_from_spec(spec)
        sys.modules["arxiv_config"] = arxiv_module
        spec.loader.exec_module(arxiv_module)

        if hasattr(arxiv_module, 'QUERY_CONFIGS'):
            collections.append(from_arxiv_config(arxiv_module.QUERY_CONFIGS))

    merged = merge_collections(*collections)

    if output_path:
        merged.save(output_path)

    return merged


if __name__ == "__main__":
    # Example: migrate existing configs
    import os

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    hn_path = os.path.join(base_dir, "HackerNewsTracking", "src_select", "filter_config.py")
    arxiv_path = os.path.join(base_dir, "Arxiv_monitoring", "config.py")
    output_path = os.path.join(base_dir, "unified", "query", "migrated_queries.json")

    print(f"Migrating configs from:")
    print(f"  HN: {hn_path}")
    print(f"  arXiv: {arxiv_path}")

    collection = migrate_existing_configs(
        hn_config_path=hn_path if os.path.exists(hn_path) else None,
        arxiv_config_path=arxiv_path if os.path.exists(arxiv_path) else None,
        output_path=output_path,
    )

    print(f"\nMigrated {len(collection)} queries to: {output_path}")
    for query_id in collection.list_ids():
        query = collection.get(query_id)
        print(f"  - {query_id}: {query.name} ({len(query.terms)} terms)")
