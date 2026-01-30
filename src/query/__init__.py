"""
Unified Query System for sci_watch.

This module provides a unified way to filter articles from different
sources (HackerNews, arXiv, etc.) using boolean expressions.

Basic Usage:
    from unified.query import Query, HackerNewsAdapter, ArxivAdapter

    # Create a query
    query = Query(
        name="AI Topics",
        description="Articles about AI and machine learning",
        terms=[
            '"artificial intelligence"',
            '"machine learning"',
            '"LLM" OR "large language model"',
        ],
        categories=["cs.AI", "cs.CL"],  # Optional, for arXiv
    )

    # Filter HackerNews articles
    hn_adapter = HackerNewsAdapter()
    matching_articles = hn_adapter.filter(articles, query)

    # Filter arXiv papers
    arxiv_adapter = ArxivAdapter()
    matching_papers = arxiv_adapter.filter(papers, query)

    # Or generate native arXiv API query
    arxiv_query_string = arxiv_adapter.to_native_query(query)

Query Syntax:
    - Exact phrases: "machine learning"
    - Word matching: python (matches word boundaries)
    - AND operator: "AI" AND "agents"
    - OR operator: "AI" OR "ML"
    - NOT operator: NOT "crypto"
    - Parentheses: ("AI" OR "ML") AND "research"

    Terms within a Query are combined with OR by default.
"""

from .query import (
    Query,
    QueryCollection,
    filter_items,
    classify_items,
)

from .adapters import (
    BaseAdapter,
    HackerNewsAdapter,
    ArxivAdapter,
    GenericAdapter,
    get_adapter,
    filter_items as adapter_filter_items,
)

from .filter_engine import (
    parse_expression,
    evaluate_expression,
    FilterNode,
    TermNode,
    AndNode,
    OrNode,
    NotNode,
)

from .config import (
    UNIFIED_QUERIES,
    get_default_collection,
    get_query,
    list_available_queries,
)

from .migration import (
    from_hackernews_config,
    from_arxiv_config,
    merge_collections,
    migrate_existing_configs,
)

from .loader import (
    load_query,
    load_query_file,
    load_all_queries,
    load_queries_by_source,
    list_query_files,
    save_query,
    delete_query,
    get_queries_dir,
)

__all__ = [
    # Query classes
    'Query',
    'QueryCollection',
    # Adapters
    'BaseAdapter',
    'HackerNewsAdapter',
    'ArxivAdapter',
    'GenericAdapter',
    'get_adapter',
    # Filter functions
    'filter_items',
    'classify_items',
    'adapter_filter_items',
    # Low-level filter engine
    'parse_expression',
    'evaluate_expression',
    'FilterNode',
    'TermNode',
    'AndNode',
    'OrNode',
    'NotNode',
    # Config
    'UNIFIED_QUERIES',
    'get_default_collection',
    'get_query',
    'list_available_queries',
    # Migration
    'from_hackernews_config',
    'from_arxiv_config',
    'merge_collections',
    'migrate_existing_configs',
    # Loader
    'load_query',
    'load_query_file',
    'load_all_queries',
    'load_queries_by_source',
    'list_query_files',
    'save_query',
    'delete_query',
    'get_queries_dir',
]
