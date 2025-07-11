import streamlit as st

st.set_page_config(
    page_title="Hello",
    page_icon="👋",
)

st.write("# Welcome to Robert's Spotify ISRC Finder!👋")

st.sidebar.success("Please select a page")

st.markdown(
    """
    ---
    ## 👈 Please select a page on the sidebar 
    """
)