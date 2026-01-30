#!/usr/bin/env python3
"""
Run all saved queries against HackerNews and arXiv.

Outputs are saved to:
- outputs/HN/{query_id}_{date}.json
- outputs/arxiv/{query_id}_{date}.json
"""

import json
import os
import sys
import argparse
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from unified.query import load_all_queries, load_query, list_query_files, HackerNewsAdapter, ArxivAdapter
from unified.apis import hackernews, arxiv_api


def get_output_dirs():
    """Get output directory paths."""
    base = PROJECT_ROOT / "outputs"
    hn_dir = base / "HN"
    arxiv_dir = base / "arxiv"

    hn_dir.mkdir(parents=True, exist_ok=True)
    arxiv_dir.mkdir(parents=True, exist_ok=True)

    return hn_dir, arxiv_dir


def run_hackernews_query(query, adapter, articles, query_id, output_dir, date_str):
    """
    Filter HackerNews articles with a query and save results.

    Args:
        query: Query object
        adapter: HackerNewsAdapter instance
        articles: Pre-fetched articles
        query_id: Query identifier
        output_dir: Output directory path
        date_str: Date string for filename

    Returns:
        Number of matching articles
    """
    matching = adapter.filter_with_matches(articles, query)

    output = {
        "query_id": query_id,
        "query_name": query.name,
        "fetch_date": datetime.now().isoformat(),
        "source": "hackernews",
        "total_fetched": len(articles),
        "total_matching": len(matching),
        "articles": matching,
    }

    filename = output_dir / f"{query_id}_{date_str}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    return len(matching)


def run_arxiv_query(query, adapter, query_id, output_dir, date_str, days_back=7):
    """
    Fetch and filter arXiv papers with a query and save results.

    Args:
        query: Query object
        adapter: ArxivAdapter instance
        query_id: Query identifier
        output_dir: Output directory path
        date_str: Date string for filename
        days_back: Days to look back for papers

    Returns:
        Number of matching papers
    """
    # Fetch papers using query terms and categories
    papers = arxiv_api.fetch_by_terms(
        terms=query.terms,
        categories=query.categories if query.categories else None,
        days_back=days_back,
        verbose=False,
    )

    # Optionally apply local filtering for more precision
    matching = adapter.filter_with_matches(papers, query)

    output = {
        "query_id": query_id,
        "query_name": query.name,
        "fetch_date": datetime.now().isoformat(),
        "source": "arxiv",
        "days_back": days_back,
        "categories": query.categories,
        "total_fetched": len(papers),
        "total_matching": len(matching),
        "papers": matching,
    }

    filename = output_dir / f"{query_id}_{date_str}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    return len(matching)


def main():
    parser = argparse.ArgumentParser(
        description="Run all saved queries against HackerNews and arXiv"
    )
    parser.add_argument(
        "-q", "--queries",
        nargs="+",
        default=None,
        help="Specific query IDs to run (default: all)"
    )
    parser.add_argument(
        "--hn-only",
        action="store_true",
        help="Only run HackerNews queries"
    )
    parser.add_argument(
        "--arxiv-only",
        action="store_true",
        help="Only run arXiv queries"
    )
    parser.add_argument(
        "-d", "--days",
        type=int,
        default=7,
        help="Days to look back for arXiv (default: 7)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    # Get output directories
    hn_dir, arxiv_dir = get_output_dirs()
    date_str = datetime.now().strftime("%Y-%m-%d_%H:%M")

    # Determine which queries to run
    if args.queries:
        query_ids = args.queries
    else:
        query_ids = list_query_files()

    if not query_ids:
        print("No queries found in queries/ folder.")
        return 1

    print(f"Running {len(query_ids)} queries: {query_ids}")
    print(f"Date: {date_str}")
    print()

    # Initialize adapters
    hn_adapter = HackerNewsAdapter()
    arxiv_adapter = ArxivAdapter()

    # Fetch HackerNews front page once (shared across all queries)
    hn_articles = []
    if not args.arxiv_only:
        print("Fetching HackerNews front page...")
        hn_articles_1 = hackernews.get_front_page(hits_per_page=100)
        hn_articles = hackernews.get_top_articles(hits_per_page=100, min_points=30)
        hn_articles = hn_articles_1 + hn_articles
        print(f"  Fetched {len(hn_articles)} articles from front page")
        print()

    # Run each query
    results = {"hackernews": {}, "arxiv": {}}

    for query_id in query_ids:
        try:
            query = load_query(query_id)
            print(f"[{query_id}] {query.name}")

            # HackerNews
            if not args.arxiv_only and hn_articles:
                count = run_hackernews_query(
                    query, hn_adapter, hn_articles,
                    query_id, hn_dir, date_str
                )
                results["hackernews"][query_id] = count
                print(f"  HN: {count} matches -> outputs/HN/{query_id}_{date_str}.json")

            # arXiv
            if not args.hn_only:
                count = run_arxiv_query(
                    query, arxiv_adapter,
                    query_id, arxiv_dir, date_str,
                    days_back=args.days
                )
                results["arxiv"][query_id] = count
                print(f"  arXiv: {count} matches -> outputs/arxiv/{query_id}_{date_str}.json")

        except Exception as e:
            print(f"  ERROR: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()

    # Summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)

    if results["hackernews"]:
        print("\nHackerNews:")
        for qid, count in results["hackernews"].items():
            print(f"  {qid}: {count} articles")

    if results["arxiv"]:
        print("\narXiv:")
        for qid, count in results["arxiv"].items():
            print(f"  {qid}: {count} papers")

    print()
    print(f"Results saved to: {PROJECT_ROOT / 'outputs'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
