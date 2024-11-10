# google_auth.py

import os
from google.oauth2.credentials import Credentials
import google_auth_oauthlib.flow
import google.auth.transport.requests
import googleapiclient.discovery

CLIENT_SECRETS_FILE = 'client_secret.json'
SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']

def authenticate_google():
    creds = None
    token_path = 'token.json'

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(google.auth.transport.requests.Request())
        else:
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_path, 'w') as token_file:
            token_file.write(creds.to_json())
    return creds

def initialize_youtube_api():
    creds = authenticate_google()
    youtube = googleapiclient.discovery.build('youtube', 'v3', credentials=creds)
    return youtube
