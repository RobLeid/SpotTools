import requests
import base64
from dotenv import load_dotenv
import os
import pandas as pd
import streamlit as st
from io import BytesIO
from PIL import Image
from urllib.request import urlopen

# Load environment variables
load_dotenv()

client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")

# Get Spotify access token
def get_access_token(client_id, client_secret):
    auth_url = 'https://accounts.spotify.com/api/token'
    auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode('utf-8')
    headers = {
        'Authorization': f'Basic {auth_header}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {
        'grant_type': 'client_credentials'
    }
    response = requests.post(auth_url, headers=headers, data=data)
    return response.json()['access_token']

# Parse album ID from URI or plain ID
def parse_album_id(user_input):
    if user_input.startswith("spotify:album:"):
        return user_input.split(":")[2]
    elif user_input.startswith("spotify:"):
        st.error("This is not an album URI. Please enter a valid album URI or ID.")
        return None
    else:
        return user_input.strip()

# Get all track IDs from album
def get_album_tracks(album_id, access_token):
    url = f"https://api.spotify.com/v1/albums/{album_id}"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    data = response.json()

    if "tracks" not in data:
        st.error("Could not retrieve album data. Please check the album ID or URI.")
        return [], None, None

    track_ids = [track["id"] for track in data["tracks"]["items"]]
    album_name = data["name"]
    album_image_url = data["images"][0]["url"] if data["images"] else None
    return track_ids, album_name, album_image_url

# Get metadata for track IDs
def get_tracks(track_ids, access_token):
    base_url = "https://api.spotify.com/v1/tracks"
    headers = {"Authorization": f"Bearer {access_token}"}
    tracks = []

    id_chunks = [track_ids[i:i+50] for i in range(0, len(track_ids), 50)]
    for chunk in id_chunks:
        ids_param = ",".join(chunk)
        response = requests.get(f"{base_url}?ids={ids_param}", headers=headers)
        data = response.json()
        if "tracks" in data:
            tracks.extend(data["tracks"])
        else:
            st.error(f"Error fetching track data: {data}")
    return tracks

# Convert DataFrame to Excel
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Tracks')
    output.seek(0)
    return output

# Streamlit app
def main():
    st.title("💿 Spotify Album Track Info Finder")
    user_input = st.text_input("Enter a Spotify album URI or album ID")

    if user_input:
        album_id = parse_album_id(user_input)
        if not album_id:
            return

        access_token = get_access_token(client_id, client_secret)
        track_ids, album_name, album_image_url = get_album_tracks(album_id, access_token)

        if not track_ids:
            return

        tracks = get_tracks(track_ids, access_token)

        simplified_data = [{
            "Track Name": t["name"],
            "Album Name": t["album"]["name"],
            "Artist(s)": ", ".join([artist["name"] for artist in t["artists"]]),
            "ISRC": t.get("external_ids", {}).get("isrc", "N/A"),
            "Spotify URL": t["external_urls"]["spotify"]
        } for t in tracks]

        df = pd.DataFrame(simplified_data)
        st.dataframe(df)

        excel_data = to_excel(df)
        st.download_button(
            label="📥 Download as Excel",
            data=excel_data,
            file_name=f"{album_name}_tracks.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        if album_image_url:
            st.markdown("### Album Artwork")
            image = Image.open(urlopen(album_image_url))
            st.image(image, caption=album_name, use_container_width=True)

if __name__ == "__main__":
    main()
