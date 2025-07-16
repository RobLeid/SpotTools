import streamlit as st
import requests

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