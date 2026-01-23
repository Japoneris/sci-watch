"""
arXiv API client.

Uses the official arxiv Python library to fetch papers.
Documentation: https://arxiv.org/help/api

Note: This module is named arxiv_api to avoid conflicts with the arxiv library.
"""

import arxiv
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone


@dataclass
class ArxivPaper:
    """Represents an arXiv paper."""
    arxiv_id: str
    title: str
    summary: str
    authors: List[str]
    published: str
    updated: str
    categories: List[str]
    primary_category: str
    arxiv_url: str
    pdf_url: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "arxiv_id": self.arxiv_id,
            "title": self.title,
            "summary": self.summary,
            "authors": self.authors,
            "published": self.published,
            "updated": self.updated,
            "categories": self.categories,
            "primary_category": self.primary_category,
            "arxiv_url": self.arxiv_url,
            "pdf_url": self.pdf_url,
        }

    @classmethod
    def from_result(cls, result: arxiv.Result) -> "ArxivPaper":
        """Create from arxiv library Result object."""
        return cls(
            arxiv_id=result.entry_id.split("/")[-1],
            title=result.title,
            summary=result.summary.replace("\n", " ").strip(),
            authors=[author.name for author in result.authors],
            published=result.published.isoformat(),
            updated=result.updated.isoformat(),
            categories=list(result.categories),
            primary_category=result.primary_category,
            arxiv_url=result.entry_id,
            pdf_url=result.pdf_url,
        )


class ArxivAPI:
    """Client for the arXiv API."""

    def __init__(
        self,
        page_size: int = 100,
        delay_between_requests: float = 1.0,
    ):
        """
        Initialize the arXiv client.

        Args:
            page_size: Number of results per API request (max 2000)
            delay_between_requests: Seconds to wait between paginated requests
        """
        self.client = arxiv.Client()
        self.page_size = page_size
        self.delay = delay_between_requests

    def search(
        self,
        query: str,
        max_results: Optional[int] = None,
        sort_by: arxiv.SortCriterion = arxiv.SortCriterion.SubmittedDate,
        sort_order: arxiv.SortOrder = arxiv.SortOrder.Descending,
    ) -> List[ArxivPaper]:
        """
        Search arXiv with a query string.

        Args:
            query: arXiv query string (see https://arxiv.org/help/api/user-manual)
            max_results: Maximum papers to return (None for all matching)
            sort_by: Sort criterion
            sort_order: Sort order

        Returns:
            List of ArxivPaper objects
        """
        search = arxiv.Search(
            query=query,
            max_results=max_results or 10000,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        papers = []
        for result in self.client.results(search):
            papers.append(ArxivPaper.from_result(result))
            if max_results and len(papers) >= max_results:
                break

        return papers

    def search_recent(
        self,
        query: str,
        days_back: int = 7,
        max_results: Optional[int] = None,
        verbose: bool = False,
    ) -> List[ArxivPaper]:
        """
        Search arXiv for recent papers within a date range.

        Handles pagination automatically and respects rate limits.

        Args:
            query: arXiv query string
            days_back: Only include papers from the last N days
            max_results: Maximum papers to return
            verbose: Print progress information

        Returns:
            List of ArxivPaper objects within the date range
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)

        search = arxiv.Search(
            query=query,
            max_results=10000,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )

        papers = []
        start = 0
        request_count = 0

        while max_results is None or len(papers) < max_results:
            if request_count > 0:
                if verbose:
                    print(f"Rate limiting: waiting {self.delay}s...")
                time.sleep(self.delay)

            request_count += 1
            if verbose:
                print(f"Fetching page {request_count} (offset: {start})...")

            page_results = []
            result_iter = self.client.results(search, offset=start)

            for i, result in enumerate(result_iter):
                if i >= self.page_size:
                    break
                page_results.append(result)

            if not page_results:
                if verbose:
                    print("No more results.")
                break

            papers_in_range = 0
            papers_outside_range = 0

            for result in page_results:
                if result.published >= cutoff_date:
                    papers.append(ArxivPaper.from_result(result))
                    papers_in_range += 1
                    if max_results and len(papers) >= max_results:
                        break
                else:
                    papers_outside_range += 1

            if verbose:
                print(f"  Found {papers_in_range} papers in date range.")

            # Stop if we got fewer results than requested (end of results)
            if len(page_results) < self.page_size:
                break

            # Stop if all papers are outside date range (sorted by date desc)
            if papers_outside_range == len(page_results):
                if verbose:
                    print("All papers outside date range, stopping.")
                break

            start += len(page_results)

        if verbose:
            print(f"Total requests: {request_count}, Total papers: {len(papers)}")

        return papers

    def fetch_by_ids(self, arxiv_ids: List[str]) -> List[ArxivPaper]:
        """
        Fetch specific papers by their arXiv IDs.

        Args:
            arxiv_ids: List of arXiv IDs (e.g., ["2301.00001", "2301.00002"])

        Returns:
            List of ArxivPaper objects
        """
        search = arxiv.Search(id_list=arxiv_ids)
        papers = []
        for result in self.client.results(search):
            papers.append(ArxivPaper.from_result(result))
        return papers


def build_query(
    terms: List[str],
    categories: Optional[List[str]] = None,
) -> str:
    """
    Build an arXiv query string from terms and categories.

    Args:
        terms: List of search terms (can include boolean operators)
        categories: Optional list of arXiv categories (e.g., ["cs.AI", "cs.CL"])

    Returns:
        arXiv query string
    """
    if not terms:
        return ""

    # Combine terms with OR
    terms_query = " OR ".join(f"({term})" for term in terms)

    # Add category filter if specified
    if categories:
        cat_query = " OR ".join(f"cat:{cat}" for cat in categories)
        return f"({terms_query}) AND ({cat_query})"

    return terms_query


# Module-level convenience functions

_default_client = None


def _get_client() -> ArxivAPI:
    global _default_client
    if _default_client is None:
        _default_client = ArxivAPI()
    return _default_client


def search(
    query: str,
    max_results: Optional[int] = 100,
) -> List[Dict[str, Any]]:
    """Search arXiv and return papers as dictionaries."""
    client = _get_client()
    papers = client.search(query, max_results)
    return [p.to_dict() for p in papers]


def search_recent(
    query: str,
    days_back: int = 7,
    max_results: Optional[int] = None,
    verbose: bool = False,
) -> List[Dict[str, Any]]:
    """Search for recent papers and return as dictionaries."""
    client = _get_client()
    papers = client.search_recent(query, days_back, max_results, verbose)
    return [p.to_dict() for p in papers]


def fetch_by_terms(
    terms: List[str],
    categories: Optional[List[str]] = None,
    days_back: int = 7,
    max_results: Optional[int] = None,
    verbose: bool = False,
) -> List[Dict[str, Any]]:
    """
    Fetch papers matching terms and categories.

    This is the main function for fetching papers using the unified query format.

    Args:
        terms: List of search terms
        categories: Optional category filter
        days_back: Days to look back
        max_results: Maximum results
        verbose: Print progress

    Returns:
        List of paper dictionaries
    """
    query = build_query(terms, categories)
    if not query:
        return []
    return search_recent(query, days_back, max_results, verbose)


def fetch_by_ids(arxiv_ids: List[str]) -> List[Dict[str, Any]]:
    """Fetch specific papers by ID and return as dictionaries."""
    client = _get_client()
    papers = client.fetch_by_ids(arxiv_ids)
    return [p.to_dict() for p in papers]
