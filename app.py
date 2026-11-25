import streamlit as st

st.set_page_config(page_title="GCP Cost Dashboard", layout="wide")

pages = st.navigation([
    st.Page("views/gcp.py", title="GCP All Services", default=True),
    st.Page("views/bigquery.py", title="BigQuery"),
])
pages.run()
