import os
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import google.auth.transport.requests
from google.oauth2.credentials import Credentials

# Path to the JSON file with your client secrets
CLIENT_SECRETS_FILE = 'client_secret.json'

# Define the API scopes
SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']  # Replace with the specific Google API scopes you need

# Authenticate and authorize
def authenticate_google():
    creds = None
    token_path = 'token.json'

    # Check if token file already exists
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    # If no valid token, do the authorization flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(google.auth.transport.requests.Request())
        else:
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for future use
        with open(token_path, 'w') as token_file:
            token_file.write(creds.to_json())

    return creds

# Example usage with YouTube API
def main():
    creds = authenticate_google()
    youtube = googleapiclient.discovery.build('youtube', 'v3', credentials=creds)

    # Sample API call to retrieve channel details
    request = youtube.channels().list(
        part='snippet,contentDetails,statistics',
        mine=True
    )
    response = request.execute()

    print(response)

if __name__ == "__main__":
    main()