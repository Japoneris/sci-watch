import streamlit as st
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.apis import hackernews, arxiv_api, html_parser
from src.query.query import Query
from src.query.loader import save_query, list_query_files, get_queries_dir
import json

st.title("Query Builder & Tester")


def load_query_raw(query_id: str) -> dict:
    """Load raw query data including source."""
    queries_dir = get_queries_dir()
    filepath = queries_dir / f"{query_id}.json"
    with open(filepath, 'r') as f:
        return json.load(f)


# Mode selection: Create new or Edit existing
existing_queries = list_query_files()
mode_options = ["Create new query"] + [f"Edit: {q}" for q in existing_queries]

selected_mode = st.selectbox(
    "Mode",
    options=mode_options,
    key="query_mode",
)

is_editing = selected_mode.startswith("Edit: ")
editing_query_id = selected_mode.replace("Edit: ", "") if is_editing else None

# Load existing query data if editing
if is_editing and editing_query_id:
    if st.session_state.get("loaded_query_id") != editing_query_id:
        query_data = load_query_raw(editing_query_id)
        st.session_state["loaded_query_id"] = editing_query_id
        st.session_state["edit_query_id"] = editing_query_id
        st.session_state["edit_query_name"] = query_data.get("name", "")
        st.session_state["edit_query_description"] = query_data.get("description", "")
        st.session_state["edit_query_terms"] = "\n".join(query_data.get("terms", []))
        st.session_state["edit_query_categories"] = ", ".join(query_data.get("categories", []))
        st.session_state["edit_query_source"] = query_data.get("source", "hackernews")
else:
    # Clear edit state when switching to create mode
    if st.session_state.get("loaded_query_id"):
        st.session_state["loaded_query_id"] = None
        st.session_state["edit_query_id"] = ""
        st.session_state["edit_query_name"] = ""
        st.session_state["edit_query_description"] = ""
        st.session_state["edit_query_terms"] = ""
        st.session_state["edit_query_categories"] = ""
        st.session_state["edit_query_source"] = "hackernews"

st.markdown("""
Test search queries against HackerNews or arXiv APIs before saving them.
""")

# Source selection - use loaded value when editing
default_source_index = 0
if is_editing and st.session_state.get("edit_query_source") == "arxiv":
    default_source_index = 1

source = st.radio(
    "Select source",
    options=["hackernews", "arxiv"],
    horizontal=True,
    index=default_source_index,
)

st.divider()

# Query configuration form
st.subheader("Query Configuration")

col1, col2 = st.columns(2)

with col1:
    query_id = st.text_input(
        "Query ID",
        value=st.session_state.get("edit_query_id", ""),
        placeholder="my_query",
        help="Unique identifier (will be filename)",
        disabled=is_editing,  # Can't change ID when editing
    )
    query_name = st.text_input(
        "Query Name",
        value=st.session_state.get("edit_query_name", ""),
        placeholder="My Query Topic",
        help="Human-readable name",
    )

with col2:
    query_description = st.text_area(
        "Description",
        value=st.session_state.get("edit_query_description", ""),
        placeholder="Description of what this query matches...",
        height=100,
    )

# Terms input
st.markdown("### Search Terms")
st.markdown("""
Enter one term per line. Syntax:
- `"exact phrase"` - matches exact phrase (case insensitive)
- `word` - matches whole word with word boundaries
- `"term1" AND "term2"` - both must match
- `"term1" OR "term2"` - either must match
- `NOT "term"` - exclude matches
- `("a" OR "b") AND "c"` - use parentheses for grouping
""")

terms_text = st.text_area(
    "Terms (one per line)",
    value=st.session_state.get("edit_query_terms", ""),
    height=150,
    placeholder='"machine learning"\n"artificial intelligence"\n"neural network" AND NOT "biology"',
)

# Parse terms from text area
terms = [t.strip() for t in terms_text.strip().split("\n") if t.strip()]

# Categories (for arXiv)
categories = []
if source == "arxiv":
    st.markdown("### arXiv Categories")
    st.markdown("Optional: filter by arXiv categories (e.g., cs.AI, cs.CL, stat.ML)")
    categories_text = st.text_input(
        "Categories (comma separated)",
        value=st.session_state.get("edit_query_categories", ""),
        placeholder="cs.AI, cs.CL, cs.LG",
    )
    if categories_text.strip():
        categories = [c.strip() for c in categories_text.split(",") if c.strip()]

st.divider()

# Test section
st.subheader("Test Query")

if source == "hackernews":
    max_results = st.number_input("Max results from front page", min_value=5, max_value=50, value=30)
else:  # arxiv
    col1, col2 = st.columns(2)
    with col1:
        max_results = st.number_input("Max results", min_value=5, max_value=100, value=20)
    with col2:
        days_back = st.number_input("Days back", min_value=1, max_value=30, value=7)

# Test button
if st.button("Test Query", type="primary"):
    if not terms:
        st.error("Please enter at least one search term.")
    else:
        with st.spinner("Fetching results..."):
            try:
                if source == "hackernews":
                    # Fetch current front page, then filter locally
                    all_articles = hackernews.get_front_page(hits_per_page=max_results)

                    # Apply local filtering with Query
                    query_obj = Query(
                        name=query_name or "Test",
                        terms=terms,
                    )
                    results = []
                    matched_ids = set()
                    for r in all_articles:
                        text = f"{r.get('title', '')} {r.get('story_text', '')}"
                        if query_obj.matches(text):
                            r_copy = r.copy()
                            r_copy['_matched_on'] = 'title'
                            results.append(r_copy)
                            matched_ids.add(r['id'])

                    # Store all articles and query for page content filtering
                    st.session_state["hn_all_articles"] = all_articles
                    st.session_state["hn_matched_ids"] = matched_ids
                    st.session_state["hn_query_obj"] = query_obj
                    st.session_state["hn_page_content_cache"] = None  # Reset cache
                else:
                    # For arXiv, build query and search
                    all_articles = None  # Not applicable for arXiv
                    arxiv_query = arxiv_api.build_query(terms, categories if categories else None)
                    results = arxiv_api.search_recent(
                        query=arxiv_query,
                        days_back=days_back,
                        max_results=max_results,
                    )

                st.success(f"Found {len(results)} results")

                # Store results in session state for display
                st.session_state["test_results"] = results
                st.session_state["test_source"] = source

            except Exception as e:
                st.error(f"Error: {e}")

# Page content filtering for HackerNews
if (st.session_state.get("test_source") == "hackernews" and
    st.session_state.get("hn_all_articles") and
    st.session_state.get("hn_query_obj")):

    all_articles = st.session_state["hn_all_articles"]
    matched_ids = st.session_state.get("hn_matched_ids", set())
    query_obj = st.session_state["hn_query_obj"]
    non_matching_count = len([a for a in all_articles if a['id'] not in matched_ids and a.get('url')])

    if non_matching_count > 0:
        st.markdown("---")
        st.markdown(f"**{non_matching_count} articles** didn't match on title. Check their page content?")

        if st.button("Also check page content", type="secondary"):
            with st.spinner(f"Fetching page content for {non_matching_count} articles..."):
                try:
                    # Prefetch all page content once
                    page_content_cache = {}
                    progress_bar = st.progress(0)
                    articles_with_urls = [a for a in all_articles if a.get('url') and a['id'] not in matched_ids]

                    for i, article in enumerate(articles_with_urls):
                        article_id = article['id']
                        url = article['url']
                        page_content, error = html_parser.fetch_page_content_verbose(url)
                        if page_content is not None:
                            page_content_cache[article_id] = page_content
                        progress_bar.progress((i + 1) / len(articles_with_urls))

                    progress_bar.empty()

                    # Apply filter to cached content
                    page_matches = []
                    for article in articles_with_urls:
                        article_id = article['id']
                        page_content = page_content_cache.get(article_id)
                        if page_content and query_obj.matches(page_content):
                            article_copy = article.copy()
                            article_copy['_matched_on'] = 'page_content'
                            page_matches.append(article_copy)

                    # Add page matches to results
                    if page_matches:
                        st.session_state["test_results"].extend(page_matches)
                        for a in page_matches:
                            matched_ids.add(a['id'])
                        st.session_state["hn_matched_ids"] = matched_ids
                        st.success(f"Found {len(page_matches)} additional matches from page content!")
                        st.rerun()
                    else:
                        st.info("No additional matches found in page content.")

                except Exception as e:
                    st.error(f"Error fetching page content: {e}")

# Display results
if "test_results" in st.session_state and st.session_state["test_results"]:
    results = st.session_state["test_results"]
    test_source = st.session_state.get("test_source", source)

    if test_source == "hackernews":
        for article in results:
            title = article.get("title", "No title")
            url = article.get("url", "")
            points = article.get("points", 0)
            hn_id = article.get("id", "")
            hn_url = f"https://news.ycombinator.com/item?id={hn_id}"
            matched_on = article.get("_matched_on", "title")

            badge = " *(via page)*" if matched_on == "page_content" else ""
            st.markdown(f"**{points} pts** - [{title}]({url}) [[HN]({hn_url})]{badge}")
    else:  # arxiv
        for paper in results:
            title = paper.get("title", "No title")
            arxiv_url = paper.get("arxiv_url", "")
            authors = ", ".join(paper.get("authors", [])[:3])
            if len(paper.get("authors", [])) > 3:
                authors += " et al."
            cats = ", ".join(paper.get("categories", []))
            published = paper.get("published", "")[:10]

            with st.expander(f"{title}"):
                st.markdown(f"**Authors:** {authors}")
                st.markdown(f"**Published:** {published}")
                st.markdown(f"**Categories:** {cats}")
                st.markdown(f"**Link:** [{arxiv_url}]({arxiv_url})")
                st.markdown("**Abstract:**")
                st.markdown(paper.get("summary", "No summary"))

st.divider()

# Save section
st.subheader("Save Query")

current_existing_queries = list_query_files()
if current_existing_queries and not is_editing:
    st.info(f"Existing queries: {', '.join(current_existing_queries)}")

save_button_label = "Update Query" if is_editing else "Save Query"
if st.button(save_button_label):
    # Use editing_query_id when editing (since the text input is disabled)
    effective_query_id = editing_query_id if is_editing else query_id

    if not effective_query_id:
        st.error("Please enter a Query ID.")
    elif not query_name:
        st.error("Please enter a Query Name.")
    elif not terms:
        st.error("Please enter at least one search term.")
    elif not is_editing and effective_query_id in current_existing_queries:
        st.error(f"Query ID '{effective_query_id}' already exists. Choose a different ID.")
    else:
        try:
            query_obj = Query(
                name=query_name,
                description=query_description,
                terms=terms,
                categories=categories,
            )
            filepath = save_query(effective_query_id, query_obj, source=source)
            action = "updated" if is_editing else "saved"
            st.success(f"Query {action}: {filepath}")
        except Exception as e:
            st.error(f"Error saving query: {e}")
