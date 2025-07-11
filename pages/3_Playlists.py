import requests
import base64
import pandas as pd
import streamlit as st
from io import BytesIO
import re

# Load environment variables
client_id = st.secrets["CLIENT_ID"]
client_secret = st.secrets["CLIENT_SECRET"]

# Get Spotify access token
def get_access_token(client_id, client_secret):
    auth_url = 'https://accounts.spotify.com/api/token'
    auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode('utf-8')
    headers = {
        'Authorization': f'Basic {auth_header}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {'grant_type': 'client_credentials'}
    response = requests.post(auth_url, headers=headers, data=data)
    return response.json()['access_token']

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

# Get all tracks from playlist (with pagination)
def get_playlist_tracks(playlist_id, access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
    tracks = []
    offset = 0
    limit = 100

    while True:
        response = requests.get(f"{url}?offset={offset}&limit={limit}", headers=headers)
        data = response.json()
        items = data.get("items", [])
        if not items:
            break
        tracks.extend(items)
        offset += limit
        if len(items) < limit:
            break

    return tracks

# Convert DataFrame to Excel
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Playlist')
    output.seek(0)
    return output

# Streamlit app
def main():
    st.title("📃 Spotify Playlist Info Finder")
    user_input = st.text_input("Enter a Spotify playlist URI, URL, or ID")

    if user_input:
        playlist_id = parse_playlist_id(user_input)
        access_token = get_access_token(client_id, client_secret)
        playlist_tracks = get_playlist_tracks(playlist_id, access_token)

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
        else:
            st.warning("No tracks found or invalid playlist.")

if __name__ == "__main__":
    main()
