#!/usr/bin/env python3
"""
Run all saved queries against HackerNews and arXiv.

Outputs are saved to:
- outputs/HN/{query_id}_{date}.json
- outputs/arxiv/{query_id}_{date}.json
"""

import json
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.query import load_query, list_query_files, HackerNewsAdapter, ArxivAdapter
from src.apis import hackernews, arxiv_api, html_parser


# =============================================================================
# Output helpers
# =============================================================================

def get_output_dirs():
    """Get output directory paths."""
    base = PROJECT_ROOT / "outputs"
    hn_dir = base / "HN"
    arxiv_dir = base / "arxiv"

    hn_dir.mkdir(parents=True, exist_ok=True)
    arxiv_dir.mkdir(parents=True, exist_ok=True)

    return hn_dir, arxiv_dir


def save_json(data: Dict[str, Any], filepath: Path):
    """Save data to JSON file."""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# =============================================================================
# HackerNews processing
# =============================================================================

def fetch_hn_articles(
    min_points: int = 30,
    days_back: int = 1,
    hits_per_page: int = 100
) -> List[Dict[str, Any]]:
    """
    Fetch HackerNews articles (front page + top articles).

    Args:
        min_points: Minimum points for top articles (default: 30)
        days_back: Number of days to look back for top articles (default: 1)
        hits_per_page: Max articles to fetch per source (default: 100)

    Returns:
        Combined list of front page and top articles
    """
    front_page = hackernews.get_front_page(hits_per_page=hits_per_page)
    top_articles = hackernews.get_top_articles(
        hits_per_page=hits_per_page,
        min_points=min_points,
        days_back=days_back
    )
    return front_page + top_articles


def prefetch_page_content(
    articles: List[Dict[str, Any]],
    verbose: bool = False
) -> Dict[str, str]:
    """
    Prefetch HTML page content for all articles.

    Returns a dict mapping article_id -> page_content.
    Articles without URLs or with fetch errors are omitted.
    """
    cache = {}
    articles_with_urls = [a for a in articles if a.get('url')]

    if verbose:
        print(f"  Prefetching page content for {len(articles_with_urls)} articles...")

    for i, article in enumerate(articles_with_urls):
        article_id = article['id']
        url = article['url']

        page_content, error = html_parser.fetch_page_content_verbose(url)
        if page_content is not None:
            cache[article_id] = page_content
        elif verbose:
            print(f"    [{i+1}/{len(articles_with_urls)}] Skip: {article.get('title', '')[:40]}... ({error})")

    if verbose:
        print(f"  Prefetched {len(cache)} pages successfully")

    return cache


def filter_hn_by_page_content(
    articles: List[Dict[str, Any]],
    query,
    matched_ids: set,
    page_content_cache: Dict[str, str],
    verbose: bool = False
) -> List[Dict[str, Any]]:
    """
    Filter articles by checking their HTML page content.

    Uses pre-fetched page content from cache.
    Only processes articles not already in matched_ids.
    """
    matches = []
    non_matching = [a for a in articles if a['id'] not in matched_ids]

    if verbose and non_matching:
        print(f"    Checking page content for {len(non_matching)} non-matching articles...")

    for article in non_matching:
        article_id = article['id']

        # Use cached page content
        page_content = page_content_cache.get(article_id)
        if page_content is None:
            continue

        matched_terms = query.get_matching_terms(page_content)
        if matched_terms:
            article_copy = article.copy()
            article_copy['_matched_terms'] = matched_terms
            article_copy['_matched_on'] = 'page_content'
            matches.append(article_copy)
            if verbose:
                print(f"      Match: {article.get('title', '')[:40]}... (via page content)")

    return matches


def process_hn_query(
    query,
    adapter: HackerNewsAdapter,
    articles: List[Dict[str, Any]],
    page_content_cache: Dict[str, str] = None,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Process a single query against HackerNews articles.

    Args:
        query: Query object with filter terms
        adapter: HackerNewsAdapter for filtering
        articles: List of HN articles
        page_content_cache: Pre-fetched page content (article_id -> content).
                           If None, page content filtering is skipped.
        verbose: Print detailed output

    Returns dict with matching articles and metadata.
    """
    # First pass: filter on title + description
    matching = adapter.filter_with_matches(articles, query)
    matched_ids = {a['id'] for a in matching}

    # Second pass: check page content for non-matching articles
    page_content_matches = 0
    if page_content_cache is not None:
        page_matches = filter_hn_by_page_content(
            articles, query, matched_ids, page_content_cache, verbose
        )
        matching.extend(page_matches)
        page_content_matches = len(page_matches)

    return {
        "total_fetched": len(articles),
        "total_matching": len(matching),
        "matched_on_title": len(matching) - page_content_matches,
        "matched_on_page_content": page_content_matches,
        "articles": matching,
    }


def run_hackernews(
    query_ids: List[str],
    output_dir: Path,
    date_str: str,
    check_page_content: bool = True,
    min_points: int = 30,
    days_back: int = 1,
    verbose: bool = False
) -> Dict[str, int]:
    """
    Run all queries against HackerNews.

    Args:
        query_ids: List of query IDs to run
        output_dir: Directory to save results
        date_str: Date string for output filenames
        check_page_content: Whether to check HTML page content
        min_points: Minimum points for top articles (default: 30)
        days_back: Number of days to look back for top articles (default: 1)
        verbose: Print detailed output

    Returns dict mapping query_id to match count.
    """
    print("=" * 60)
    print("HACKERNEWS")
    print("=" * 60)

    # Fetch articles once
    print("Fetching articles...")
    print(f"  Looking back {days_back} day(s), min points: {min_points}")
    articles = fetch_hn_articles(
        min_points=min_points,
        days_back=days_back
    )
    print(f"  Fetched {len(articles)} articles")

    # Prefetch page content once (reused across all queries)
    page_content_cache = None
    if check_page_content:
        print("  Page content checking: enabled")
        page_content_cache = prefetch_page_content(articles, verbose=verbose)
    else:
        print("  Page content checking: disabled")
    print()

    adapter = HackerNewsAdapter()
    results = {}

    for query_id in query_ids:
        try:
            query = load_query(query_id)
            print(f"[{query_id}] {query.name}")

            result = process_hn_query(
                query, adapter, articles,
                page_content_cache=page_content_cache,
                verbose=verbose
            )

            # Save output
            output = {
                "query_id": query_id,
                "query_name": query.name,
                "fetch_date": datetime.now().isoformat(),
                "source": "hackernews",
                **result
            }
            filename = output_dir / f"{query_id}_{date_str}.json"
            save_json(output, filename)

            count = result["total_matching"]
            results[query_id] = count
            print(f"  {count} matches (title: {result['matched_on_title']}, "
                  f"page: {result['matched_on_page_content']})")

        except Exception as e:
            print(f"  ERROR: {e}")
            if verbose:
                import traceback
                traceback.print_exc()

    print()
    return results


# =============================================================================
# arXiv processing
# =============================================================================

def process_arxiv_query(
    query,
    adapter: ArxivAdapter,
    days_back: int = 1
) -> Dict[str, Any]:
    """
    Process a single query against arXiv.

    Returns dict with matching papers and metadata.
    """
    # Fetch papers using query terms and categories
    papers = arxiv_api.fetch_by_terms(
        terms=query.terms,
        categories=query.categories if query.categories else None,
        days_back=days_back,
        verbose=False,
    )

    # Apply local filtering for more precision
    matching = adapter.filter_with_matches(papers, query)

    return {
        "days_back": days_back,
        "categories": query.categories,
        "total_fetched": len(papers),
        "total_matching": len(matching),
        "papers": matching,
    }


def run_arxiv(
    query_ids: List[str],
    output_dir: Path,
    date_str: str,
    days_back: int = 1,
    verbose: bool = False
) -> Dict[str, int]:
    """
    Run all queries against arXiv.

    Returns dict mapping query_id to match count.
    """
    print("=" * 60)
    print("ARXIV")
    print("=" * 60)
    print(f"Looking back {days_back} day(s)")
    print()

    adapter = ArxivAdapter()
    results = {}

    for query_id in query_ids:
        try:
            query = load_query(query_id)
            print(f"[{query_id}] {query.name}")

            result = process_arxiv_query(query, adapter, days_back=days_back)

            # Save output
            output = {
                "query_id": query_id,
                "query_name": query.name,
                "fetch_date": datetime.now().isoformat(),
                "source": "arxiv",
                **result
            }
            filename = output_dir / f"{query_id}_{date_str}.json"
            save_json(output, filename)

            count = result["total_matching"]
            results[query_id] = count
            print(f"  {count} matches (fetched {result['total_fetched']} papers)")

        except Exception as e:
            print(f"  ERROR: {e}")
            if verbose:
                import traceback
                traceback.print_exc()

    print()
    return results


# =============================================================================
# Main
# =============================================================================

def print_summary(hn_results: Dict[str, int], arxiv_results: Dict[str, int]):
    """Print summary of results."""
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)

    if hn_results:
        print("\nHackerNews:")
        for qid, count in hn_results.items():
            print(f"  {qid}: {count} articles")

    if arxiv_results:
        print("\narXiv:")
        for qid, count in arxiv_results.items():
            print(f"  {qid}: {count} papers")

    print()
    print(f"Results saved to: {PROJECT_ROOT / 'outputs'}")


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
        default=1,
        help="Days to look back (applies to both arXiv and HN top articles, default: 1)"
    )
    parser.add_argument(
        "--hn-min-points",
        type=int,
        default=30,
        help="Minimum points for HN top articles (default: 30)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--no-hn-page-content",
        action="store_true",
        help="Disable fetching HTML page content for HN articles"
    )

    args = parser.parse_args()

    # Determine which queries to run
    query_ids = args.queries if args.queries else list_query_files()
    if not query_ids:
        print("No queries found in queries/ folder.")
        return 1

    # Setup
    hn_dir, arxiv_dir = get_output_dirs()
    date_str = datetime.now().strftime("%Y-%m-%d_%H:%M")

    print(f"Running {len(query_ids)} queries: {query_ids}")
    print(f"Date: {date_str}")
    print()

    # Process each source
    hn_results = {}
    arxiv_results = {}

    if not args.arxiv_only:
        hn_results = run_hackernews(
            query_ids, hn_dir, date_str,
            check_page_content=not args.no_hn_page_content,
            min_points=args.hn_min_points,
            days_back=args.days,
            verbose=args.verbose
        )

    if not args.hn_only:
        arxiv_results = run_arxiv(
            query_ids, arxiv_dir, date_str,
            days_back=args.days,
            verbose=args.verbose
        )

    print_summary(hn_results, arxiv_results)
    return 0


if __name__ == "__main__":
    sys.exit(main())
