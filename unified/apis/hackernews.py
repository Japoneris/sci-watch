"""
HackerNews API client.

Documentation:
- https://hn.algolia.com/api
- https://github.com/HackerNews/API

Available tags for filtering:
- story, comment, poll, pollopt
- show_hn, ask_hn, front_page
- author_:USERNAME
- story_:ID
"""

import requests
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


BASE_URL = "http://hn.algolia.com/api/v1/"


@dataclass
class HNArticle:
    """Represents a HackerNews article/story."""
    id: str
    title: str
    url: str
    points: int
    num_comments: int
    created_at: str
    author: str = ""
    story_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "points": self.points,
            "num_comments": self.num_comments,
            "created_at": self.created_at,
            "author": self.author,
            "story_text": self.story_text,
        }

    @classmethod
    def from_hit(cls, hit: Dict[str, Any]) -> "HNArticle":
        """Create from Algolia API hit."""
        return cls(
            id=hit.get("objectID", ""),
            title=hit.get("title", ""),
            url=hit.get("url", ""),
            points=hit.get("points", 0) or 0,
            num_comments=hit.get("num_comments", 0) or 0,
            created_at=hit.get("created_at", ""),
            author=hit.get("author", ""),
            story_text=hit.get("story_text", "") or "",
        )


class HackerNewsAPI:
    """Client for the HackerNews Algolia API."""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url

    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make a GET request to the API."""
        url = f"{self.base_url}{endpoint}"
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def get_item(self, item_id: int) -> Dict[str, Any]:
        """
        Get an item by its ID.

        Args:
            item_id: The HN item ID

        Returns:
            Item data including children (comments)
        """
        return self._get(f"items/{item_id}")

    def get_user(self, username: str) -> Dict[str, Any]:
        """
        Get a user by username.

        Args:
            username: The HN username

        Returns:
            User data
        """
        return self._get(f"users/{username}")

    def search(
        self,
        query: str = "",
        tags: str = "story",
        page: int = 0,
        hits_per_page: int = 50,
        sort_by_date: bool = False,
    ) -> Dict[str, Any]:
        """
        Search HackerNews.

        Args:
            query: Search query string
            tags: Filter by tags (story, comment, front_page, etc.)
            page: Page number (0-indexed)
            hits_per_page: Results per page (max 1000)
            sort_by_date: If True, sort by date instead of relevance

        Returns:
            Raw API response with 'hits', 'nbHits', 'nbPages', etc.
        """
        endpoint = "search_by_date" if sort_by_date else "search"
        params = {
            "query": query,
            "tags": tags,
            "page": page,
            "hitsPerPage": hits_per_page,
        }
        return self._get(endpoint, params)

    def search_articles(
        self,
        query: str = "",
        tags: str = "story",
        page: int = 0,
        hits_per_page: int = 50,
        sort_by_date: bool = False,
    ) -> List[HNArticle]:
        """
        Search for articles and return parsed results.

        Args:
            query: Search query string
            tags: Filter by tags
            page: Page number
            hits_per_page: Results per page
            sort_by_date: Sort by date instead of relevance

        Returns:
            List of HNArticle objects
        """
        response = self.search(
            query=query,
            tags=tags,
            page=page,
            hits_per_page=hits_per_page,
            sort_by_date=sort_by_date,
        )
        return [HNArticle.from_hit(hit) for hit in response.get("hits", [])]

    def get_front_page(self, hits_per_page: int = 30) -> List[HNArticle]:
        """
        Get current front page articles.

        This is the primary method for fetching HN content - it only returns
        articles currently on the front page, not historical content.

        Args:
            hits_per_page: Number of articles to fetch (max ~30 on front page)

        Returns:
            List of front page articles
        """
        return self.search_articles(
            query="",
            tags="front_page",
            hits_per_page=hits_per_page,
        )

    def get_comments(self, item_id: int) -> List[Dict[str, Any]]:
        """
        Get first-level comments for an item.

        Args:
            item_id: The HN item ID

        Returns:
            List of comment dictionaries
        """
        item = self.get_item(item_id)
        children = item.get("children", [])
        return [
            {
                "id": comment.get("id"),
                "text": comment.get("text", ""),
                "author": comment.get("author", ""),
                "children": [c.get("id") for c in comment.get("children", [])],
            }
            for comment in children
        ]


# Module-level convenience functions

_default_client = None


def _get_client() -> HackerNewsAPI:
    global _default_client
    if _default_client is None:
        _default_client = HackerNewsAPI()
    return _default_client


def get_front_page(hits_per_page: int = 30) -> List[Dict[str, Any]]:
    """
    Get current front page articles as dictionaries.

    This is the primary function for fetching HN content - it only returns
    articles currently on the front page, not historical content.
    """
    client = _get_client()
    articles = client.get_front_page(hits_per_page)
    return [a.to_dict() for a in articles]


def get_item(item_id: int) -> Dict[str, Any]:
    """Get an item by ID."""
    client = _get_client()
    return client.get_item(item_id)


def get_comments(item_id: int) -> List[Dict[str, Any]]:
    """Get first-level comments for an item."""
    client = _get_client()
    return client.get_comments(item_id)
