import streamlit as st

# Main navigation
pg = st.navigation([
    st.Page("pages/hn_tracking.py", title="HackerNews - Topic Tracking", icon="🔍"),
    st.Page("pages/arxiv_tracking.py", title="ArXiv - Topic Tracking", icon="🔍"),
    st.Page("pages/query_builder.py", title="Query Builder", icon="🛠"),
])

pg.run()