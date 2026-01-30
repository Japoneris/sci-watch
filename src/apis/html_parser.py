"""
HTML page parser for extracting text content from web pages.

Uses BeautifulSoup to fetch and parse HTML pages, extracting
the body text content with all HTML tags stripped.
"""

import requests
from typing import Optional


def fetch_page_content(url: str, timeout: int = 10) -> Optional[str]:
    """
    Fetch a web page and extract the body text content.

    Args:
        url: The URL to fetch
        timeout: Request timeout in seconds

    Returns:
        The extracted text content from the page body, or None if fetch fails
    """
    if not url:
        return None

    try:
        from bs4 import BeautifulSoup
    except ImportError:
        raise ImportError(
            "beautifulsoup4 is required for HTML parsing. "
            "Install it with: pip install beautifulsoup4"
        )

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; SciWatch/1.0; +https://github.com/sci-watch)'
        }
        response = requests.get(url, timeout=timeout, headers=headers)
        response.raise_for_status()

        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')

        # Remove script and style elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            element.decompose()

        # Get the body element
        body = soup.find('body')
        if body is None:
            # Fallback to entire document if no body tag
            body = soup

        # Extract text, stripping all HTML
        text = body.get_text(separator=' ', strip=True)

        # Clean up excessive whitespace
        text = ' '.join(text.split())

        return text

    except requests.RequestException:
        return None
    except Exception:
        return None


def fetch_page_content_verbose(url: str, timeout: int = 10) -> tuple[Optional[str], Optional[str]]:
    """
    Fetch a web page and extract the body text content, with error details.

    Args:
        url: The URL to fetch
        timeout: Request timeout in seconds

    Returns:
        Tuple of (content, error_message). If successful, error_message is None.
        If failed, content is None and error_message describes the failure.
    """
    if not url:
        return None, "No URL provided"

    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return None, "beautifulsoup4 not installed"

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; SciWatch/1.0; +https://github.com/sci-watch)'
        }
        response = requests.get(url, timeout=timeout, headers=headers)
        response.raise_for_status()

        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')

        # Remove script and style elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            element.decompose()

        # Get the body element
        body = soup.find('body')
        if body is None:
            body = soup

        # Extract text, stripping all HTML
        text = body.get_text(separator=' ', strip=True)
        text = ' '.join(text.split())

        return text, None

    except requests.Timeout:
        return None, f"Timeout after {timeout}s"
    except requests.HTTPError as e:
        return None, f"HTTP {e.response.status_code}"
    except requests.RequestException as e:
        return None, f"Request failed: {type(e).__name__}"
    except Exception as e:
        return None, f"Parse error: {type(e).__name__}"
