from fastapi import FastAPI, BackgroundTasks
import asyncio
import os
import logging
from google_auth import initialize_youtube_api
from yt_dl import download_video
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

app = FastAPI()

# Function to load the OAuth token from token.json
def load_access_token():
    token_path = './token.json'  # Path to the token file
    if os.path.exists(token_path):
        with open(token_path, 'r') as token_file:
            credentials_data = json.load(token_file)
            creds = Credentials.from_authorized_user_info(credentials_data)
            
            # If the credentials are expired, refresh them
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                
                # Save the refreshed credentials back to the token file
                with open(token_path, 'w') as token_file:
                    json.dump(creds.to_dict(), token_file)
                    
            return creds.token
    else:
        raise FileNotFoundError(f"Token file {token_path} not found.")

# Simulate video download and processing task
async def process_video(task_id: str, url: str, access_token: str):
    # Define the fixed download path
    download_path = '/Volumes/2TB_MAINDISK_FAN_XIANG/DownLoadYoutubeVideos/%(uploader)s/%(upload_date)s-%(title)s.%(ext)s'  # Replace with the desired fixed path

    # Simulate download, transcribing, and processing
    print(f"Task {task_id}: Downloading video from {url}...")
    
    # Call the download function with the fixed path and access token
    await asyncio.to_thread(download_video, url, access_token, download_path)
    
    print(f"Task {task_id}: Video downloaded.")

    # Simulate transcription (you would call Whisper API here)
    await asyncio.sleep(5)
    print(f"Task {task_id}: Audio transcribed.")
    
    # Simulate GPT processing
    await asyncio.sleep(3)
    print(f"Task {task_id}: Text formatted.")

@app.post("/process_video/")
async def create_task(background_tasks: BackgroundTasks, task_id: str, url: str):
    try:
        access_token = load_access_token()  # Load the access token from the token.json file
    except FileNotFoundError as e:
        return {"error": str(e)}
    
    # Add background task to process the video
    background_tasks.add_task(process_video, task_id, url, access_token)
    
    return {"message": f"Task {task_id} started."}

@app.get("/task_status/{task_id}")
async def get_task_status(task_id: str):
    # You can manage task status via Redis or another store if required
    return {"task_id": task_id, "status": "Processing..."}

if __name__ == "__main__":
    # Initialize the YouTube API here for other functionality (if needed)
    youtube = initialize_youtube_api()

    # Example API call (you can replace with a real call to get video details)
    request = youtube.channels().list(part='snippet,contentDetails,statistics', mine=True)
    response = request.execute()
    print(response)

    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)