import re
import streamlit as st

def parse_artist_id(user_input):
    user_input = user_input.strip()
    if user_input.startswith("spotify:artist:"):
        return user_input.split(":")[2]
    elif "open.spotify.com/artist/" in user_input:
        match = re.search(r"spotify\.com/artist/([a-zA-Z0-9]+)", user_input)
        return match.group(1) if match else None
    else:
        return user_input

def parse_album_id(user_input):
    user_input = user_input.strip()

    if user_input.startswith("spotify:album:"):
        return user_input.split(":")[2]
    elif "open.spotify.com/album/" in user_input:
        match = re.search(r"spotify\.com/album/([a-zA-Z0-9]+)", user_input)
        if match:
            return match.group(1)
        else:
            st.error("Invalid album URL. Could not extract album ID.")
            return None
    elif user_input.startswith("spotify:"):
        st.error("This is not an album URI. Please enter a valid album URI, URL, or ID.")
        return None
    else:
        return user_input

def parse_track_ids(user_input):
    raw_items = [item.strip() for item in user_input.splitlines() if item.strip()]
    track_ids = []

    for item in raw_items:
        if item.startswith("spotify:"):
            parts = item.split(":")
            if len(parts) == 3 and parts[1] == "track":
                track_ids.append(parts[2])
            else:
                st.error(f"Invalid URI: '{item}' is not a track URI.")
        elif "open.spotify.com" in item:
            match = re.search(r"spotify\.com/track/([a-zA-Z0-9]{22})", item)
            if match:
                track_ids.append(match.group(1))
            else:
                st.error(f"Invalid URL: '{item}' does not contain a valid track ID.")
        else:
            if re.fullmatch(r"[a-zA-Z0-9]{22}", item):
                track_ids.append(item)
            else:
                st.error(f"Invalid ID: '{item}' is not a valid Spotify track ID.")

    return track_ids

