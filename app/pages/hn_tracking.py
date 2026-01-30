import streamlit as st
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Configuration
OUTPUTS_DIR = Path(__file__).parent.parent.parent / "outputs" / "HN"

st.title("HackerNews - Topic Tracking")


def load_available_files():
    """Load list of available HN JSON files."""
    if not OUTPUTS_DIR.exists():
        return []
    return sorted(OUTPUTS_DIR.glob("*.json"))


def load_json_file(filepath):
    """Load and parse a JSON file."""
    with open(filepath, "r") as f:
        return json.load(f)


def deduplicate(articles):
    """Deduplicate articles, keeping the one with highest points for each ID."""
    seen = {}
    for article in articles:
        article_id = article.get('id')
        if article_id is None:
            continue
        
        if article_id not in seen:
            seen[article_id] = article
        else:
            # Keep the article with higher points
            if article.get('points', 0) > seen[article_id].get('points', 0):
                seen[article_id] = article
    
    return list(seen.values())


def load_all_data():
    """Load all topic files and return combined data."""
    files = load_available_files()
    all_data = {}
    for f in files:
        data = load_json_file(f)
        topic_name = data.get("query_name", data.get("query_id", f.stem))
        if topic_name not in all_data:
            all_data[topic_name] = data["articles"]
        else:
            all_data[topic_name].extend(data["articles"])

    deduplicate_data = {}
    for topic, articles in all_data.items():
        deduplicate_data[topic] = deduplicate(articles)
                         
    return deduplicate_data




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
        return dt.strftime("%Y-%m-%d %H:%M")
    except:
        return date_str


# Load all data
all_data = load_all_data()

if not all_data:
    st.warning("No HackerNews data files found in outputs/HN/")
    st.stop()

# Sidebar filters
with st.sidebar:
    st.header("Filters")
    min_points = st.number_input("Minimum points", min_value=0, value=50, step=10)

# Build combined articles list with topic info
all_articles_with_topic = []
for topic_name, data in all_data.items():
    for article in data:
        article_copy = article.copy()
        article_copy["_topic"] = topic_name
        article_copy["_week"] = get_week_key(article.get("created_at", ""))
        all_articles_with_topic.append(article_copy)

# Build weekly counts for chart
weekly_counts_by_topic = defaultdict(lambda: defaultdict(int))
weekly_counts_all = defaultdict(int)

for article in all_articles_with_topic:
    week = article["_week"]
    topic = article["_topic"]
    weekly_counts_by_topic[topic][week] += 1
    weekly_counts_all[week] += 1

# Get all weeks sorted
all_weeks = sorted(set(weekly_counts_all.keys()), key=get_week_start)

# Chart section
st.subheader("Articles Published Per Week")

split_by_topic = st.toggle("Split by topic", value=False)

if split_by_topic:
    # Build DataFrame with one column per topic
    chart_data = {}
    for topic in all_data.keys():
        chart_data[topic] = [weekly_counts_by_topic[topic].get(week, 0) for week in all_weeks]
    df = pd.DataFrame(chart_data, index=all_weeks)
else:
    # Single line for all topics combined
    chart_data = {"All Topics": [weekly_counts_all.get(week, 0) for week in all_weeks]}
    df = pd.DataFrame(chart_data, index=all_weeks)

st.line_chart(df)

# Topic selector
st.divider()
st.subheader("Browse Articles by Topic")

topic_names = list(all_data.keys())
selected_topic = st.selectbox(
    "Select a topic",
    options=topic_names,
    format_func=lambda x: x.replace("_", " ").title()
)

# Get articles for selected topic
articles = all_data[selected_topic]

# Display topic metadata
col1, col2 = st.columns(2)
with col1:
    st.metric("Total Articles", len(articles))

if not articles:
    st.info("No articles found for this topic.")
    st.stop()

# Group articles by week
articles_by_week = defaultdict(list)
for article in articles:
    week = get_week_key(article.get("created_at", ""))
    articles_by_week[week].append(article)

# Sort weeks (newest first)
sorted_weeks = sorted(articles_by_week.keys(), key=get_week_start, reverse=True)

# Display articles grouped by week
st.divider()
st.subheader("Articles by Week")

for week in sorted_weeks:

    with st.expander(f"Week: {week} ({len(articles_by_week[week])} articles)"):
        week_articles = articles_by_week[week]
        # Filter by minimum points
        week_articles_filtered = [a for a in week_articles if a.get("points", 0) >= min_points]

        if not week_articles_filtered:
            continue

        # Sort by points within week (high to low)
        week_articles_sorted = sorted(week_articles_filtered, key=lambda x: x.get("points", 0), reverse=True)

        st.markdown(f"### {week} ({len(week_articles_filtered)} articles)")

        lst = []
        for article in week_articles_sorted:
            hn_url = f"https://news.ycombinator.com/item?id={article.get('id', '')}"
            lst.append(f"- {article.get('points', 0)} pt  [[Link](<{article['url']}>) / [HN](<{hn_url}>)] {article['title']} ")

        week_markdown = "\n".join(lst)
        st.markdown(week_markdown)

        # Download button for markdown
        filename = f"{week}.md"
        st.download_button(
            label=f"Download {week} markdown",
            data=week_markdown,
            file_name=filename,
            mime="text/markdown"
        )

