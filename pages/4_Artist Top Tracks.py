import requests
import base64
import pandas as pd
import streamlit as st
from io import BytesIO
from PIL import Image
from urllib.request import urlopen
import re

from utils.auth import get_access_token
from utils.tools import to_excel
from utils.parse import parse_artist_id

# Get artist metadata and top tracks
def get_artist_metadata_and_top_tracks(artist_id, access_token, market="US"):
    headers = {"Authorization": f"Bearer {access_token}"}
    artist_url = f"https://api.spotify.com/v1/artists/{artist_id}"
    top_tracks_url = f"{artist_url}/top-tracks?market={market}"

    artist_response = requests.get(artist_url, headers=headers).json()
    top_tracks_response = requests.get(top_tracks_url, headers=headers).json()

    artist_name = artist_response.get("name", "Unknown Artist")
    artist_image_url = artist_response["images"][0]["url"] if artist_response.get("images") else None
    top_tracks = top_tracks_response.get("tracks", [])

    return artist_name, artist_image_url, top_tracks

# Streamlit app
def main():
    st.title("🎤 Spotify Artist Top Tracks")
    user_input = st.text_input("Enter a Spotify artist URI, URL, or ID")

    if user_input:
        artist_id = parse_artist_id(user_input)
        access_token = get_access_token()
        artist_name, artist_image_url, top_tracks = get_artist_metadata_and_top_tracks(artist_id, access_token)

        if top_tracks:
            simplified_data = [{
                "Track Name": t["name"],
                "Album Name": t["album"]["name"],
                "Artist(s)": ", ".join([artist["name"] for artist in t["artists"]]),
                "ISRC": t.get("external_ids", {}).get("isrc", "N/A"),
                "Spotify URL": t["external_urls"]["spotify"]
            } for t in top_tracks]

            df = pd.DataFrame(simplified_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

            excel_data = to_excel(df)
            st.download_button(
                label="📥 Download as Excel",
                data=excel_data,
                file_name="artist_top_tracks.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        if artist_image_url:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(' ')
            with col2:
                 st.image(artist_image_url, caption=artist_name, width=300)
            with col3:
                st.write(' ')

        else:
            st.warning("No top tracks found or invalid artist.")

if __name__ == "__main__":
    main()
