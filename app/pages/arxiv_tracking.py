import streamlit as st
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Configuration
OUTPUTS_DIR = Path(__file__).parent.parent.parent / "outputs" / "arxiv"

st.title("ArXiv - Topic Tracking")


def load_available_files():
    """Load list of available ArXiv JSON files."""
    if not OUTPUTS_DIR.exists():
        return []
    return sorted(OUTPUTS_DIR.glob("*.json"))


def load_json_file(filepath):
    """Load and parse a JSON file."""
    with open(filepath, "r") as f:
        return json.load(f)


def load_all_data():
    """Load all topic files and return combined data."""
    files = load_available_files()
    all_data = {}
    for f in files:
        data = load_json_file(f)
        topic_name = data.get("query_name", data.get("query_id", f.stem))
        all_data[topic_name] = data
    return all_data


def get_week_key(date_str):
    """Convert ISO date string to week key (YYYY-WXX)."""
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        year, week, _ = dt.isocalendar()
        return f"{year}-W{week:02d}"
    except:
        return "Unknown"


def get_week_start(week_key):
    """Convert week key to Monday date for sorting."""
    try:
        year, week = week_key.split("-W")
        return datetime.strptime(f"{year}-W{week}-1", "%Y-W%W-%w")
    except:
        return datetime.min


def format_date(date_str):
    """Format ISO date string to readable format."""
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except:
        return date_str


# Load all data
all_data = load_all_data()

if not all_data:
    st.warning("No ArXiv data files found in outputs/arxiv/")
    st.stop()

# Build combined papers list with topic info and collect all categories
all_papers_with_topic = []
all_categories = set()
for topic_name, data in all_data.items():
    for paper in data.get("papers", []):
        paper_copy = paper.copy()
        paper_copy["_topic"] = topic_name
        paper_copy["_week"] = get_week_key(paper.get("published", ""))
        all_papers_with_topic.append(paper_copy)
        all_categories.update(paper.get("categories", []))

all_categories = sorted(all_categories)

# Sidebar filters
with st.sidebar:
    st.header("Filters")
    selected_categories = st.multiselect(
        "Filter by category",
        options=all_categories,
        default=[]
    )
    search_term = st.text_input("Search in title/abstract", "")

# Build weekly counts for chart
weekly_counts_by_topic = defaultdict(lambda: defaultdict(int))
weekly_counts_all = defaultdict(int)

for paper in all_papers_with_topic:
    week = paper["_week"]
    topic = paper["_topic"]
    weekly_counts_by_topic[topic][week] += 1
    weekly_counts_all[week] += 1

# Get all weeks sorted
all_weeks = sorted(set(weekly_counts_all.keys()), key=get_week_start)

# Chart section
st.subheader("Papers Published Per Week")

split_by_topic = st.toggle("Split by topic", value=False)

if split_by_topic:
    chart_data = {}
    for topic in all_data.keys():
        chart_data[topic] = [weekly_counts_by_topic[topic].get(week, 0) for week in all_weeks]
    df = pd.DataFrame(chart_data, index=all_weeks)
else:
    chart_data = {"All Topics": [weekly_counts_all.get(week, 0) for week in all_weeks]}
    df = pd.DataFrame(chart_data, index=all_weeks)

st.line_chart(df)

# Topic selector
st.divider()
st.subheader("Browse Papers by Topic")

topic_names = list(all_data.keys())
selected_topic = st.selectbox(
    "Select a topic",
    options=topic_names,
    format_func=lambda x: x.replace("_", " ").title()
)

# Get papers for selected topic
selected_data = all_data[selected_topic]
papers = selected_data.get("papers", [])

# Display topic metadata
col1, col2 = st.columns(2)
with col1:
    st.metric("Total Papers", len(papers))
with col2:
    fetch_date = selected_data.get("fetch_date", "")
    if fetch_date:
        st.metric("Fetch Date", format_date(fetch_date))

if not papers:
    st.info("No papers found for this topic.")
    st.stop()

# Apply filters
filtered_papers = papers

if selected_categories:
    filtered_papers = [
        p for p in filtered_papers
        if any(cat in p.get("categories", []) for cat in selected_categories)
    ]

if search_term:
    search_lower = search_term.lower()
    filtered_papers = [
        p for p in filtered_papers
        if search_lower in p.get("title", "").lower() or search_lower in p.get("summary", "").lower()
    ]

# Group papers by week
papers_by_week = defaultdict(list)
for paper in filtered_papers:
    week = get_week_key(paper.get("published", ""))
    papers_by_week[week].append(paper)

# Sort weeks (newest first)
sorted_weeks = sorted(papers_by_week.keys(), key=get_week_start, reverse=True)

# Display papers grouped by week
st.divider()
st.subheader("Papers by Week")
st.write(f"Showing {len(filtered_papers)} of {len(papers)} papers")

for week in sorted_weeks:
    week_papers = papers_by_week[week]
    # Sort by published date within week (newest first)
    week_papers_sorted = sorted(week_papers, key=lambda x: x.get("published", ""), reverse=True)

    with st.expander(f"Week: {week} ({len(week_papers)} papers)"):
        for paper in week_papers_sorted:
            title = paper.get("title", "No title")
            arxiv_url = paper.get("arxiv_url", "")
            pdf_url = paper.get("pdf_url", "")
            primary_cat = paper.get("primary_category", "")
            summary = paper.get("summary", "")
            authors = paper.get("authors", [])

            cols = st.columns([1, 12])
            with cols[0]:
                with st.popover("i"):
                    st.markdown(f"**Authors:** {', '.join(authors[:5])}{' (+' + str(len(authors)-5) + ' more)' if len(authors) > 5 else ''}")
                    st.markdown(f"**Categories:** {', '.join(paper.get('categories', []))}")
                    st.markdown("**Abstract:**")
                    st.write(summary)
            with cols[1]:
                links = []
                if arxiv_url:
                    links.append(f"[ArXiv](<{arxiv_url}>)")
                if pdf_url:
                    links.append(f"[PDF](<{pdf_url}>)")
                links_str = " | ".join(links) if links else ""
                st.markdown(f"[{links_str}] **{title}** ({primary_cat})")
