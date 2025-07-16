import requests
import base64
import pandas as pd
from io import BytesIO
from PIL import Image
from urllib.request import urlopen
import re
import streamlit as st

from utils.auth import get_access_token
from utils.parse import parse_artist_id
from utils.tools import to_excel

# Spotify markets
MARKETS = [
    "AD", "AE", "AG", "AL", "AM", "AO", "AR", "AT", "AU", "AZ", "BA", "BB", "BD", "BE", "BF", "BG", "BH", "BI", "BJ",
    "BN", "BO", "BR", "BS", "BT", "BW", "BY", "BZ", "CA", "CD", "CG", "CH", "CI", "CL", "CM", "CO", "CR", "CV", "CY",
    "CZ", "DE", "DJ", "DK", "DM", "DO", "DZ", "EC", "EE", "EG", "ES", "FI", "FJ", "FM", "FR", "GA", "GB", "GD", "GE",
    "GH", "GM", "GN", "GQ", "GR", "GT", "GW", "GY", "HK", "HN", "HR", "HT", "HU", "ID", "IE", "IL", "IN", "IQ", "IS",
    "IT", "JM", "JO", "JP", "KE", "KG", "KH", "KI", "KM", "KN", "KR", "KW", "KZ", "LA", "LB", "LC", "LI", "LK", "LR",
    "LS", "LT", "LU", "LV", "LY", "MA", "MC", "MD", "ME", "MG", "MH", "MK", "ML", "MN", "MO", "MR", "MT", "MU", "MV",
    "MW", "MX", "MY", "MZ", "NA", "NE", "NG", "NI", "NL", "NO", "NP", "NR", "NZ", "OM", "PA", "PE", "PG", "PH", "PK",
    "PL", "PS", "PT", "PW", "PY", "QA", "RO", "RS", "RW", "SA", "SB", "SC", "SE", "SG", "SI", "SK", "SL", "SM", "SN",
    "SR", "ST", "SV", "SZ", "TD", "TG", "TH", "TJ", "TL", "TN", "TO", "TR", "TT", "TV", "TZ", "UA", "UG", "US", "UY",
    "UZ", "VC", "VE", "VN", "VU", "WS", "XK", "ZA", "ZM", "ZW"
]

def get_artist_albums(artist_id, market, access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    albums = []
    url = f"https://api.spotify.com/v1/artists/{artist_id}/albums"
    params = {"limit": 50, "offset": 0, "market": market, "include_groups": "album,single,compilation"}

    while True:
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        items = data.get("items", [])
        if not items:
            break
        albums.extend(items)
        if data.get("next") is None:
            break
        params["offset"] += 50

    seen = set()
    unique_albums = []
    for album in albums:
        if album["id"] not in seen:
            seen.add(album["id"])
            unique_albums.append(album)
    return unique_albums

def get_album_details(album_id, access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    album_url = f"https://api.spotify.com/v1/albums/{album_id}"
    album_data = requests.get(album_url, headers=headers).json()

    album_name = album_data.get("name", "Unknown Album")
    album_image_url = album_data["images"][0]["url"] if album_data.get("images") else None
    upc = album_data.get("external_ids", {}).get("upc", "N/A")
    label = album_data.get("label", "N/A")
    release_date = album_data.get("release_date", "N/A")
    release_type = album_data.get("album_type", "N/A").capitalize()
    album_artists = ", ".join([a["name"] for a in album_data.get("artists", [])])

    p_line = "N/A"
    for c in album_data.get("copyrights", []):
        if c.get("type") == "P":
            p_line = c.get("text", "N/A")
            break

    # Paginate through all tracks and collect metadata
    track_items = []
    track_ids = []
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
        track_ids.extend([t["id"] for t in items])
        if data.get("next") is None:
            break
        offset += limit

    # Fetch full track metadata (for ISRCs, explicit, duration)
    full_tracks = []
    for i in range(0, len(track_ids), 50):
        ids_chunk = ",".join(track_ids[i:i+50])
        track_response = requests.get(f"https://api.spotify.com/v1/tracks?ids={ids_chunk}", headers=headers)
        full_tracks.extend(track_response.json().get("tracks", []))

    # Combine metadata
    tracks = []
    for meta, full in zip(track_items, full_tracks):
        duration_ms = full.get("duration_ms", 0)
        minutes = duration_ms // 60000
        seconds = (duration_ms % 60000) // 1000
        duration_str = f"{minutes}:{seconds:02d}"

        tracks.append({
            "Disc Number": meta.get("disc_number", "N/A"),
            "Track Number": meta.get("track_number", "N/A"),
            "Track Name": full.get("name", meta.get("name")),
            "Album Name": album_name,
            "Album Artists": album_artists,
            "Track Artists": ", ".join([a["name"] for a in full.get("artists", [])]),
            "ISRC": full.get("external_ids", {}).get("isrc", "N/A"),
            "Spotify URL": full.get("external_urls", {}).get("spotify", "N/A"),
            "Explicit": full.get("explicit", False),
            "Duration": duration_str,
            "UPC": upc,
            "Label": label,
            "℗ Line": p_line,
            "Release Date": release_date,
            "Release Type": release_type
        })

    return tracks, album_name, album_image_url

def main():
    st.title("🎤 Spotify Artist Discography")

    artist_input = st.text_input("Enter Spotify Artist URI, URL, or ID")
    market = st.selectbox("Select Market (Country Code)", MARKETS, index=MARKETS.index("US"))

    if not artist_input:
        return

    with st.spinner("🔍 Parsing artist ID..."):
        artist_id = parse_artist_id(artist_input)
    if not artist_id:
        st.error("Invalid artist input.")
        return

    with st.spinner("🔑 Getting access token..."):
        access_token = get_access_token()

    with st.spinner("🎧 Fetching artist albums..."):
        albums = get_artist_albums(artist_id, market, access_token)

    if not albums:
        st.warning("No albums found for this artist in the selected market.")
        return

    grouped = {"album": [], "single": [], "compilation": []}
    for album in albums:
        grouped[album["album_type"]].append(album)

    all_dataframes = []
    album_sections = []

    for group_name, group_albums in grouped.items():
        if not group_albums:
            continue

        sorted_albums = sorted(group_albums, key=lambda x: x["release_date"], reverse=True)
        section_dataframes = []

        with st.spinner(f"📦 Processing {group_name}s..."):
            for album in sorted_albums:
                tracks, album_name, album_image_url = get_album_details(album["id"], access_token)
                df = pd.DataFrame(tracks)
                section_dataframes.append((df, album_name, album_image_url))

        album_sections.append((group_name, section_dataframes))
        all_dataframes.extend([df for df, _, _ in section_dataframes])

    if all_dataframes:
        combined_df = pd.concat(all_dataframes, ignore_index=True)
        st.download_button(
            label="📦 Download All Albums to Excel",
            data=to_excel(combined_df),
            file_name="Single_Artist_Releases.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    for group_name, section_dataframes in album_sections:
        st.header(group_name.capitalize() + "s")
        st.divider()

        for df, album_name, album_image_url in section_dataframes:
            col1, col2 = st.columns([1, 3])
            with col1:
                if album_image_url:
                    image = Image.open(urlopen(album_image_url))
                    st.image(image, caption=album_name)
                st.download_button(
                    label="📥 Download Excel",
                    data=to_excel(df),
                    file_name=f"{album_name}_tracks.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            with col2:
                st.dataframe(df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
