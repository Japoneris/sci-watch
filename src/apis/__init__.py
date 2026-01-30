"""
Unified APIs for fetching articles from different sources.

Provides clean interfaces to:
- HackerNews (via Algolia API)
- arXiv (via official API)

Basic Usage:
    from unified.apis import hackernews, arxiv_api

    # Fetch HackerNews front page (only current top page, not historical)
    articles = hackernews.get_front_page()

    # Fetch recent arXiv papers
    papers = arxiv_api.search_recent('"machine learning"', days_back=7)

    # Fetch arXiv papers by terms and categories
    papers = arxiv_api.fetch_by_terms(
        terms=['"AI agents"', '"LLM"'],
        categories=["cs.AI", "cs.CL"],
        days_back=7
    )

Integration with Query System:
    from unified.query import load_query, HackerNewsAdapter, ArxivAdapter
    from unified.apis import hackernews, arxiv_api

    # Load a unified query
    query = load_query('ai')

    # Fetch and filter HackerNews
    articles = hackernews.get_front_page(hits_per_page=100)
    adapter = HackerNewsAdapter()
    matching = adapter.filter(articles, query)

    # Fetch and filter arXiv (query provides terms and categories)
    papers = arxiv_api.fetch_by_terms(
        terms=query.terms,
        categories=query.categories,
        days_back=7
    )
    # Papers are already filtered by the API query
    # Optionally apply local filtering for more precision:
    arxiv_adapter = ArxivAdapter()
    matching = arxiv_adapter.filter(papers, query)
"""

from . import hackernews
from . import arxiv_api
from . import html_parser

__all__ = ['hackernews', 'arxiv_api', 'html_parser']
