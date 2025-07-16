import streamlit as st
import requests
import base64
import pandas as pd
import time
import re
from io import BytesIO

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
    album_data = requests.get(f"https://api.spotify.com/v1/albums/{album_id}", headers=headers).json()

    album_name = album_data.get("name", "Unknown Album")
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

    # Get all tracks (with pagination)
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

    # Get full track metadata (for ISRCs, explicit, duration)
    full_tracks = []
    for i in range(0, len(track_ids), 50):
        ids_chunk = ",".join(track_ids[i:i+50])
        track_response = requests.get(f"https://api.spotify.com/v1/tracks?ids={ids_chunk}", headers=headers)
        full_tracks.extend(track_response.json().get("tracks", []))

    tracks = []
    for meta, full in zip(track_items, full_tracks):
        duration_ms = full.get("duration_ms", 0)
        minutes = duration_ms // 60000
        seconds = (duration_ms % 60000) // 1000
        duration_str = f"{minutes}:{seconds:02d}"

        tracks.append({
            "Album Name": album_name,
            "Album Artists": album_artists,
            "Release Type": release_type,
            "Release Date": release_date,
            "UPC": upc,
            "Label": label,
            "℗ Line": p_line,
            "Disc Number": meta.get("disc_number", "N/A"),
            "Track Number": meta.get("track_number", "N/A"),
            "Track Name": full.get("name", meta.get("name")),
            "Track Artists": ", ".join([a["name"] for a in full.get("artists", [])]),
            "ISRC": full.get("external_ids", {}).get("isrc", "N/A"),
            "Spotify URL": full.get("external_urls", {}).get("spotify", "N/A"),
            "Explicit": full.get("explicit", False),
            "Duration": duration_str
        })

    return tracks

def main():
    st.title("🎶 Multiple Artist Search")

    artist_input = st.text_area("Enter multiple Spotify Artist URIs, URLs, or IDs (one per line)")
    market = st.selectbox("Select Market (Country Code)", MARKETS, index=MARKETS.index("US"))

    if st.button("🔍 Process Artists"):
        artist_ids = [parse_artist_id(line) for line in artist_input.splitlines() if line.strip()]
        artist_ids = [aid for aid in artist_ids if aid]

        if not artist_ids:
            st.error("Please enter at least one valid artist ID.")
            return

        access_token = get_access_token()
        all_data = []
        start_time = time.time()

        with st.spinner("⏳ Processing...", show_time=True):
            for i, artist_id in enumerate(artist_ids, 1):
                albums = get_artist_albums(artist_id, market, access_token)
                for album in albums:
                    tracks = get_album_details(album["id"], access_token)
                    all_data.extend(tracks)

        elapsed = time.time() - start_time
        st.success(f"✅ Done! Processed {len(artist_ids)} artist(s) in {elapsed:.2f} seconds.")

        if all_data:
            df = pd.DataFrame(all_data)
            st.download_button(
                label="📥 Download Excel File",
                data=to_excel(df),
                file_name="Multiple_Artists_Releases.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("No data was collected.")

if __name__ == "__main__":
    main()
