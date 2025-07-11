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

# Parse artist ID from URI or URL
def parse_artist_id(user_input):
    user_input = user_input.strip()
    if user_input.startswith("spotify:artist:"):
        return user_input.split(":")[2]
    elif "open.spotify.com/artist/" in user_input:
        match = re.search(r"artist/([a-zA-Z0-9]+)", user_input)
        if match:
            return match.group(1)
    return user_input

# Get top tracks for artist
def get_artist_top_tracks(artist_id, access_token, market="US"):
    url = f"https://api.spotify.com/v1/artists/{artist_id}/top-tracks?market={market}"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    return response.json().get("tracks", [])

# Convert DataFrame to Excel
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Top Tracks')
    output.seek(0)
    return output

# Streamlit app
def main():
    st.title("🎤 Spotify Artist Top Tracks Finder")
    user_input = st.text_input("Enter a Spotify artist URI, URL, or ID")

    if user_input:
        artist_id = parse_artist_id(user_input)
        access_token = get_access_token(client_id, client_secret)
        top_tracks = get_artist_top_tracks(artist_id, access_token)

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
        else:
            st.warning("No top tracks found or invalid artist.")

if __name__ == "__main__":
    main()
