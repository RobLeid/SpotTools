import requests
import base64
import pandas as pd
from io import BytesIO
from PIL import Image
from urllib.request import urlopen
import re
import streamlit as st


client_id = st.secrets["CLIENT_ID"]
client_secret = st.secrets["CLIENT_SECRET"]


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

def parse_artist_id(user_input):
    user_input = user_input.strip()
    if user_input.startswith("spotify:artist:"):
        return user_input.split(":")[2]
    elif "open.spotify.com/artist/" in user_input:
        match = re.search(r"spotify\.com/artist/([a-zA-Z0-9]+)", user_input)
        return match.group(1) if match else None
    else:
        return user_input

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

    p_line = "N/A"
    for c in album_data.get("copyrights", []):
        if c.get("type") == "P":
            p_line = c.get("text", "N/A")
            break

    # Paginate through all tracks
    tracks = []
    base_url = f"https://api.spotify.com/v1/albums/{album_id}/tracks"
    limit = 50
    offset = 0

    while True:
        response = requests.get(f"{base_url}?limit={limit}&offset={offset}", headers=headers)
        data = response.json()
        items = data.get("items", [])
        if not items:
            break

        for t in items:
            tracks.append({
                "Disc Number": t.get("disc_number", "N/A"),
                "Track Number": t.get("track_number", "N/A"),
                "Track Name": t["name"],
                "Album Name": album_name,
                "Artist(s)": ", ".join([a["name"] for a in t["artists"]]),
                "ISRC": t.get("external_ids", {}).get("isrc", "N/A"),
                "Spotify URL": t["external_urls"]["spotify"],
                "UPC": upc,
                "Label": label,
                "℗ Line": p_line,
                "Release Date": release_date
            })

        if data.get("next") is None:
            break
        offset += limit

    return tracks, album_name, album_image_url


def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Tracks')
    output.seek(0)
    return output

def main():
    st.title("🎤 Spotify Artist Discography Explorer")

    artist_input = st.text_input("Enter Spotify Artist URI, URL, or ID")
    market = st.selectbox("Select Market (Country Code)", MARKETS, index=MARKETS.index("US"))

    if not artist_input:
        return

    artist_id = parse_artist_id(artist_input)
    if not artist_id:
        st.error("Invalid artist input.")
        return

    access_token = get_access_token(client_id, client_secret)
    albums = get_artist_albums(artist_id, market, access_token)

    if not albums:
        st.warning("No albums found for this artist in the selected market.")
        return

    grouped = {"album": [], "single": [], "compilation": []}
    for album in albums:
        grouped[album["album_type"]].append(album)

    all_dataframes = []

    # Preprocess all albums and collect data
    album_sections = []
    for group_name, group_albums in grouped.items():
        if not group_albums:
            continue

        sorted_albums = sorted(group_albums, key=lambda x: x["release_date"], reverse=True)
        section_dataframes = []

        for album in sorted_albums:
            tracks, album_name, album_image_url = get_album_details(album["id"], access_token)
            df = pd.DataFrame(tracks)
            section_dataframes.append((df, album_name, album_image_url))

        album_sections.append((group_name, section_dataframes))
        all_dataframes.extend([df for df, _, _ in section_dataframes])

    # Global download button
    if all_dataframes:
        combined_df = pd.concat(all_dataframes, ignore_index=True)
        st.download_button(
            label="📦 Download All Albums to Excel",
            data=to_excel(combined_df),
            file_name="All_Artist_Releases.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # Display albums by section
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
