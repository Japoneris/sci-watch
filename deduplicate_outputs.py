#!/usr/bin/env python3
"""
Deduplicate output files.

For HackerNews:
- Groups files by query_id
- Deduplicates articles by ID, keeping the one with highest points
- Creates consolidated files and removes source files

For arXiv:
- Groups files by query_id
- Deduplicates papers by arxiv_id, keeping the most recent entry
- Creates consolidated files and removes source files
"""

import json
import os
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent


def get_output_dirs():
    """Get output directory paths."""
    hn_dir = PROJECT_ROOT / "outputs" / "HN"
    arxiv_dir = PROJECT_ROOT / "outputs" / "arxiv"
    return hn_dir, arxiv_dir


def group_files_by_query(directory: Path) -> Dict[str, List[Path]]:
    """
    Group JSON files by query_id.

    Files are named: {query_id}_{date}.json (e.g., topic_2026-01-27-14.json)
    """
    groups = defaultdict(list)

    for filepath in directory.glob("*.json"):
        # Skip already consolidated files
        if "_consolidated" in filepath.name:
            continue

        # Extract query_id (everything before the date pattern YYYY-MM-DD-HH)
        name = filepath.stem
        # Find where the date starts (format: YYYY-MM-DD-HH)
        parts = name.split("_")

        query_id_parts = []
        for i, part in enumerate(parts):
            # Check if this looks like a date (YYYY-MM-DD-HH pattern)
            if "-" in part and len(parts) > i:
                # Likely start of date pattern
                break
            query_id_parts.append(part)

        query_id = "_".join(query_id_parts) if query_id_parts else name
        groups[query_id].append(filepath)

    return dict(groups)


def deduplicate_hn_articles(
    files: List[Path],
    verbose: bool = False
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Deduplicate HackerNews articles from multiple files.

    Keeps the article with the highest points for each ID.

    Returns:
        Tuple of (deduplicated_articles, metadata)
    """
    # article_id -> (article_data, points, source_file)
    best_articles: Dict[str, Tuple[Dict, int, str]] = {}

    total_before = 0
    source_files_info = []

    for filepath in sorted(files):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"  WARNING: Could not read {filepath.name}: {e}")
            continue

        articles = data.get("articles", [])
        total_before += len(articles)

        source_files_info.append({
            "filename": filepath.name,
            "articles_count": len(articles),
            "fetch_date": data.get("fetch_date", ""),
        })

        for article in articles:
            article_id = str(article.get("id", ""))
            if not article_id:
                continue

            points = article.get("points", 0) or 0

            if article_id not in best_articles:
                best_articles[article_id] = (article, points, filepath.name)
            else:
                existing_points = best_articles[article_id][1]
                if points > existing_points:
                    best_articles[article_id] = (article, points, filepath.name)

    # Extract just the articles
    deduplicated = [item[0] for item in best_articles.values()]

    # Sort by points descending
    deduplicated.sort(key=lambda x: x.get("points", 0) or 0, reverse=True)

    metadata = {
        "source_files_count": len(files),
        "total_articles_before_dedup": total_before,
        "total_articles_after_dedup": len(deduplicated),
        "duplicates_removed": total_before - len(deduplicated),
        "source_files": source_files_info,
    }

    if verbose:
        print(f"    Files processed: {len(files)}")
        print(f"    Articles before: {total_before}")
        print(f"    Articles after: {len(deduplicated)}")
        print(f"    Duplicates removed: {total_before - len(deduplicated)}")

    return deduplicated, metadata


def deduplicate_arxiv_papers(
    files: List[Path],
    verbose: bool = False
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Deduplicate arXiv papers from multiple files.

    Keeps the most recently fetched version for each arxiv_id.

    Returns:
        Tuple of (deduplicated_papers, metadata)
    """
    # arxiv_id -> (paper_data, fetch_date, source_file)
    best_papers: Dict[str, Tuple[Dict, str, str]] = {}

    total_before = 0
    source_files_info = []

    for filepath in sorted(files):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"  WARNING: Could not read {filepath.name}: {e}")
            continue

        papers = data.get("papers", [])
        fetch_date = data.get("fetch_date", "")
        total_before += len(papers)

        source_files_info.append({
            "filename": filepath.name,
            "papers_count": len(papers),
            "fetch_date": fetch_date,
        })

        for paper in papers:
            arxiv_id = paper.get("arxiv_id", "")
            if not arxiv_id:
                continue

            if arxiv_id not in best_papers:
                best_papers[arxiv_id] = (paper, fetch_date, filepath.name)
            else:
                # Keep the more recent fetch
                existing_date = best_papers[arxiv_id][1]
                if fetch_date > existing_date:
                    best_papers[arxiv_id] = (paper, fetch_date, filepath.name)

    # Extract just the papers
    deduplicated = [item[0] for item in best_papers.values()]

    # Sort by published date descending
    deduplicated.sort(key=lambda x: x.get("published", ""), reverse=True)

    metadata = {
        "source_files_count": len(files),
        "total_papers_before_dedup": total_before,
        "total_papers_after_dedup": len(deduplicated),
        "duplicates_removed": total_before - len(deduplicated),
        "source_files": source_files_info,
    }

    if verbose:
        print(f"    Files processed: {len(files)}")
        print(f"    Papers before: {total_before}")
        print(f"    Papers after: {len(deduplicated)}")
        print(f"    Duplicates removed: {total_before - len(deduplicated)}")

    return deduplicated, metadata


def process_hackernews(
    output_dir: Path,
    dry_run: bool = False,
    verbose: bool = False,
    keep_sources: bool = False,
) -> Dict[str, int]:
    """
    Process and deduplicate all HackerNews output files.

    Returns dict of query_id -> deduplicated count
    """
    print("\n[HackerNews Deduplication]")
    print(f"  Directory: {output_dir}")

    if not output_dir.exists():
        print("  Directory not found, skipping.")
        return {}

    groups = group_files_by_query(output_dir)
    print(f"  Found {len(groups)} query groups")

    results = {}

    for query_id, files in sorted(groups.items()):
        if len(files) < 2:
            # Skip if only one file (nothing to deduplicate)
            if verbose:
                print(f"  [{query_id}] Skipping (only {len(files)} file)")
            continue

        print(f"  [{query_id}] Processing {len(files)} files...")

        if dry_run:
            # Just count without actually processing
            total = 0
            for f in files:
                try:
                    with open(f, 'r') as fp:
                        data = json.load(fp)
                        total += len(data.get("articles", []))
                except:
                    pass
            print(f"    Would process {total} articles from {len(files)} files")
            continue

        # Deduplicate
        articles, metadata = deduplicate_hn_articles(files, verbose)

        if not articles:
            print(f"    No articles found, skipping.")
            continue

        # Get query name from first file
        query_name = query_id
        try:
            with open(files[0], 'r') as f:
                first_data = json.load(f)
                query_name = first_data.get("query_name", query_id)
        except:
            pass

        # Create consolidated file
        output = {
            "query_id": query_id,
            "query_name": query_name,
            "consolidated_date": datetime.now().isoformat(),
            "source": "hackernews",
            "deduplication_info": metadata,
            "total_articles": len(articles),
            "articles": articles,
        }

        consolidated_path = output_dir / f"{query_id}_consolidated.json"
        with open(consolidated_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        print(f"    Created: {consolidated_path.name}")

        # Remove source files
        if not keep_sources:
            for filepath in files:
                filepath.unlink()
                if verbose:
                    print(f"    Removed: {filepath.name}")
            print(f"    Removed {len(files)} source files")

        results[query_id] = len(articles)

    return results


def process_arxiv(
    output_dir: Path,
    dry_run: bool = False,
    verbose: bool = False,
    keep_sources: bool = False,
) -> Dict[str, int]:
    """
    Process and deduplicate all arXiv output files.

    Returns dict of query_id -> deduplicated count
    """
    print("\n[arXiv Deduplication]")
    print(f"  Directory: {output_dir}")

    if not output_dir.exists():
        print("  Directory not found, skipping.")
        return {}

    groups = group_files_by_query(output_dir)
    print(f"  Found {len(groups)} query groups")

    results = {}

    for query_id, files in sorted(groups.items()):
        if len(files) < 2:
            if verbose:
                print(f"  [{query_id}] Skipping (only {len(files)} file)")
            continue

        print(f"  [{query_id}] Processing {len(files)} files...")

        if dry_run:
            total = 0
            for f in files:
                try:
                    with open(f, 'r') as fp:
                        data = json.load(fp)
                        total += len(data.get("papers", []))
                except:
                    pass
            print(f"    Would process {total} papers from {len(files)} files")
            continue

        # Deduplicate
        papers, metadata = deduplicate_arxiv_papers(files, verbose)

        if not papers:
            print(f"    No papers found, skipping.")
            continue

        # Get query name from first file
        query_name = query_id
        categories = []
        try:
            with open(files[0], 'r') as f:
                first_data = json.load(f)
                query_name = first_data.get("query_name", query_id)
                categories = first_data.get("categories", [])
        except:
            pass

        # Create consolidated file
        output = {
            "query_id": query_id,
            "query_name": query_name,
            "consolidated_date": datetime.now().isoformat(),
            "source": "arxiv",
            "categories": categories,
            "deduplication_info": metadata,
            "total_papers": len(papers),
            "papers": papers,
        }

        consolidated_path = output_dir / f"{query_id}_consolidated.json"
        with open(consolidated_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        print(f"    Created: {consolidated_path.name}")

        # Remove source files
        if not keep_sources:
            for filepath in files:
                filepath.unlink()
                if verbose:
                    print(f"    Removed: {filepath.name}")
            print(f"    Removed {len(files)} source files")

        results[query_id] = len(papers)

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Deduplicate HackerNews and arXiv output files"
    )
    parser.add_argument(
        "--hn-only",
        action="store_true",
        help="Only process HackerNews"
    )
    parser.add_argument(
        "--arxiv-only",
        action="store_true",
        help="Only process arXiv"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--keep-sources",
        action="store_true",
        help="Keep source files after consolidation (don't delete)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    hn_dir, arxiv_dir = get_output_dirs()

    print("=" * 60)
    print("Output Deduplication")
    print("=" * 60)

    if args.dry_run:
        print("\n*** DRY RUN - No changes will be made ***")

    hn_results = {}
    arxiv_results = {}

    if not args.arxiv_only:
        hn_results = process_hackernews(
            hn_dir,
            dry_run=args.dry_run,
            verbose=args.verbose,
            keep_sources=args.keep_sources,
        )

    if not args.hn_only:
        arxiv_results = process_arxiv(
            arxiv_dir,
            dry_run=args.dry_run,
            verbose=args.verbose,
            keep_sources=args.keep_sources,
        )

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    if hn_results:
        print("\nHackerNews consolidated:")
        for qid, count in hn_results.items():
            print(f"  {qid}: {count} articles")

    if arxiv_results:
        print("\narXiv consolidated:")
        for qid, count in arxiv_results.items():
            print(f"  {qid}: {count} papers")

    if not hn_results and not arxiv_results:
        print("\nNo files needed deduplication (each query had only 1 file)")

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
