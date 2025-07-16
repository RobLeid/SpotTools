import requests
import base64
import pandas as pd
import streamlit as st
from io import BytesIO
import re

from utils.auth import get_access_token
from utils.parse import parse_track_ids
from utils.tracks import get_tracks
from utils.tools import to_excel


def ms_to_min_sec(ms):
    minutes = ms // 60000
    seconds = (ms % 60000) // 1000
    return f"{minutes}:{seconds:02}"

# Main Streamlit app
def main():
    st.title("🎵 Spotify Track Info")
    user_input = st.text_area("Enter Spotify track IDs, URIs, or URLs (one per line)")

    if st.button("🔍 Get Track Info"):
        if not user_input.strip():
            st.warning("Please enter at least one track ID, URI, or URL.")
            return

        track_ids = parse_track_ids(user_input)

        if not track_ids:
            st.warning("No valid track IDs found.")
            return

        with st.spinner("⏳ Processing..."):
            access_token = get_access_token()
            tracks = get_tracks(track_ids, access_token)

        if tracks:
            simplified_data = [{
                "Track Artist(s)": ", ".join([artist["name"] for artist in t["artists"]]),
                "Track Name": t["name"],
                "ISRC": t.get("external_ids", {}).get("isrc", "N/A"),
                "Duration": ms_to_min_sec(t["duration_ms"]),
                "Explicit": "Yes" if t["explicit"] else "No",
                "Spotify URL": t["external_urls"]["spotify"]
            } for t in tracks]

            df = pd.DataFrame(simplified_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

            excel_data = to_excel(df)
            st.download_button(
                label="📥 Download as Excel",
                data=excel_data,
                file_name="spotify_tracks.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("No valid tracks found.")


if __name__ == "__main__":
    main()
