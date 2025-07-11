import requests
import base64
from dotenv import load_dotenv
import os
import pandas as pd
import streamlit as st
from io import BytesIO

# Load environment variables
load_dotenv()

client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")

# Function to get the access token
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
    response_data = response.json()
    return response_data['access_token']

# Function to extract track IDs from input
def parse_track_ids(user_input):
    raw_ids = [item.strip() for item in user_input.split(",")]
    track_ids = []

    for item in raw_ids:
        if item.startswith("spotify:"):
            parts = item.split(":")
            if len(parts) == 3 and parts[1] == "track":
                track_ids.append(parts[2])
            else:
                st.error(f"Invalid URI: '{item}' is not a track URI.")
        else:
            track_ids.append(item)
    
    return track_ids

# Function to get track metadata
def get_tracks(track_ids, access_token):
    base_url = "https://api.spotify.com/v1/tracks"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    tracks = []

    id_chunks = [track_ids[i:i+50] for i in range(0, len(track_ids), 50)]

    for chunk in id_chunks:
        ids_param = ",".join(chunk)
        response = requests.get(f"{base_url}?ids={ids_param}", headers=headers)
        response_data = response.json()

        if "tracks" in response_data:
            tracks.extend(response_data["tracks"])
        else:
            st.error(f"Error fetching tracks: {response_data}")
    
    return tracks

# Function to convert DataFrame to Excel
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Tracks')
    output.seek(0)
    return output

# Main Streamlit app
def main():
    st.title("🎵 Spotify Track Info Finder")
    user_input = st.text_input("Enter up to 50 Spotify track IDs or URIs (comma-separated)")

    if user_input:
        track_ids = parse_track_ids(user_input)

        if len(track_ids) > 50:
            st.warning("You entered more than 50 track IDs. Only the first 50 will be processed.")
            track_ids = track_ids[:50]

        access_token = get_access_token(client_id, client_secret)
        tracks = get_tracks(track_ids, access_token)

        if tracks:
            simplified_data = [{
                "Artist(s)": ", ".join([artist["name"] for artist in t["artists"]]),
                "Track Name": t["name"],
                "ISRC": t.get("external_ids", {}).get("isrc", "N/A"),
                "Spotify URL": t["external_urls"]["spotify"],
                "Album Name": t["album"]["name"]
            } for t in tracks]

            df = pd.DataFrame(simplified_data)
            st.dataframe(df)

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
