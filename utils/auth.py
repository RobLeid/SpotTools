import base64
import requests
import streamlit as st

def get_access_token():
    client_id = st.secrets["CLIENT_ID"]
    client_secret = st.secrets["CLIENT_SECRET"]
    auth_url = 'https://accounts.spotify.com/api/token'
    
    auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode('utf-8')
    headers = {
        'Authorization': f'Basic {auth_header}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {'grant_type': 'client_credentials'}
    
    response = requests.post(auth_url, headers=headers, data=data)
    
    if response.status_code != 200:
        st.error(f"Failed to get access token. Status code: {response.status_code}")
        st.error(f"Response text: {response.text}")
        return None
    
    try:
        response_data = response.json()
        return response_data['access_token']
    except ValueError:
        st.error("Failed to parse JSON response.")
        st.error(f"Raw response: {response.text}")
        return None
