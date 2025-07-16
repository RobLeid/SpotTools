import requests
import base64
import pandas as pd
import streamlit as st
from io import BytesIO
from PIL import Image
from urllib.request import urlopen
import re

from utils.auth import get_access_token
from utils.parse import parse_album_id
from utils.tracks import get_tracks
from utils.tools import to_excel

# Get all track IDs from album (with pagination)
def get_album_tracks(album_id, access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    album_url = f"https://api.spotify.com/v1/albums/{album_id}"

    album_response = requests.get(album_url, headers=headers)
    album_data = album_response.json()
    album_name = album_data.get("name", "Unknown Album")
    album_image_url = album_data["images"][0]["url"] if album_data.get("images") else None
    upc = album_data.get("external_ids", {}).get("upc", "N/A")
    label = album_data.get("label", "N/A")

    # Extract P-line (℗)
    p_line = "N/A"
    for copyright in album_data.get("copyrights", []):
        if copyright.get("type") == "P":
            p_line = copyright.get("text", "N/A")
            break

    # Paginate through all tracks
    track_items = []
    base_url = f"https://api.spotify.com/v1/albums/{album_id}/tracks"
    limit = 50
    offset = 0

    while True:
        response = requests.get(f"{base_url}?limit={limit}&offset={offset}", headers=headers)
        data = response.json()
        items = data.get("items", [])
        if not items:
            break
        track_items.extend(items)
        if len(items) < limit:
            break
        offset += limit

    track_ids = [track["id"] for track in track_items]
    return track_ids, album_name, album_image_url, track_items, upc, label, p_line

# Streamlit app
def main():
    st.title("💿 Spotify Album Info")

    user_input = st.text_area("Enter multiple Spotify album URIs, URLs, or IDs (one per line)")
    if not user_input:
        return

    album_inputs = [parse_album_id(line) for line in user_input.splitlines() if line.strip()]
    album_inputs = [aid for aid in album_inputs if aid]

    access_token = get_access_token()
    all_dataframes = []

    global_excel_placeholder = st.empty()

    for album_id in album_inputs:
        track_ids, album_name, album_image_url, track_items, upc, label, p_line = get_album_tracks(album_id, access_token)
        if not track_ids:
            continue

        tracks = get_tracks(track_ids, access_token)
        simplified_data = []
        for t, meta in zip(tracks, track_items):
            simplified_data.append({
                "Disc Number": meta.get("disc_number", "N/A"),
                "Track Number": meta.get("track_number", "N/A"),
                "Track Name": t["name"],
                "Album Name": t["album"]["name"],
                "Artist(s)": ", ".join([artist["name"] for artist in t["artists"]]),
                "ISRC": t.get("external_ids", {}).get("isrc", "N/A"),
                "Spotify URL": t["external_urls"]["spotify"],
                "UPC": upc,
                "Label": label,
                "℗ Line": p_line
            })

        df = pd.DataFrame(simplified_data)
        all_dataframes.append(df)

        col1, col2 = st.columns([1, 3])
        with col1:
            if album_image_url:
                image = Image.open(urlopen(album_image_url))
                st.image(image, caption=album_name)
            st.download_button(
                label=f"📥 Download Excel",
                data=to_excel(df),
                file_name=f"{album_name}_tracks.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        with col2:
            st.dataframe(df, use_container_width=True, hide_index=True)

    if all_dataframes:
        combined_df = pd.concat(all_dataframes, ignore_index=True)
        global_excel = to_excel(combined_df)
        global_excel_placeholder.download_button(
            label="📦 Download All Albums to Excel",
            data=global_excel,
            file_name="All_Albums_Tracks.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

if __name__ == "__main__":
    main()
