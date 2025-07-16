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

# Parse playlist ID from URI or URL
def parse_playlist_id(user_input):
    user_input = user_input.strip()
    if user_input.startswith("spotify:playlist:"):
        return user_input.split(":")[2]
    elif "open.spotify.com/playlist/" in user_input:
        match = re.search(r"playlist/([a-zA-Z0-9]+)", user_input)
        if match:
            return match.group(1)
    return user_input

# Get playlist metadata and tracks
def get_playlist_metadata_and_tracks(playlist_id, access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    base_url = f"https://api.spotify.com/v1/playlists/{playlist_id}"

    # Get metadata
    meta_response = requests.get(base_url, headers=headers)
    meta_data = meta_response.json()
    playlist_name = meta_data.get("name", "Unknown Playlist")
    playlist_image_url = meta_data["images"][0]["url"] if meta_data.get("images") else None

    # Get tracks with pagination
    tracks = []
    offset = 0
    limit = 100
    while True:
        response = requests.get(f"{base_url}/tracks?offset={offset}&limit={limit}", headers=headers)
        data = response.json()
        items = data.get("items", [])
        if not items:
            break
        tracks.extend(items)
        offset += limit
        if len(items) < limit:
            break

    return playlist_name, playlist_image_url, tracks

# Streamlit app
def main():
    st.title("📃 Spotify Playlist Info")
    st.caption("Note: this does not work for Spotify generated playlists...")
    user_input = st.text_input("Enter a Spotify playlist URI, URL, or ID")

    if user_input:
        playlist_id = parse_playlist_id(user_input)
        access_token = get_access_token()
        playlist_name, playlist_image_url, playlist_tracks = get_playlist_metadata_and_tracks(playlist_id, access_token)

        if playlist_tracks:
            simplified_data = []
            for item in playlist_tracks:
                track = item.get("track")
                if track:
                    simplified_data.append({
                        "Track Name": track["name"],
                        "Artist(s)": ", ".join([artist["name"] for artist in track["artists"]]),
                        "Album Name": track["album"]["name"],
                        "ISRC": track.get("external_ids", {}).get("isrc", "N/A"),
                        "Spotify URL": track["external_urls"]["spotify"]
                    })

            df = pd.DataFrame(simplified_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

            excel_data = to_excel(df)
            st.download_button(
                label="📥 Download as Excel",
                data=excel_data,
                file_name="playlist_tracks.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        if playlist_image_url:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(' ')
            with col2:
                st.image(playlist_image_url, caption=playlist_name, width=300)
            with col3:
                st.write(' ')

        else:
            st.warning("No tracks found or invalid playlist.")

if __name__ == "__main__":
    main()
