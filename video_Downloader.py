import yt_dlp
import logging
import time
import os
import json

# Load the OAuth token from the token.json file
with open('/Users/xinyiyu/Documents/GitHub/readVideo/token.json') as json_file:
    token_data = json.load(json_file)

# Extract the access token
access_token = token_data['token']

# Configure logging
logging.basicConfig(filename='yt_dlp_download.log', level=logging.INFO)

# List of video URLs to download
urls = [
    "https://www.youtube.com/watch?v=0HQ1a9uiB0o",  # Replace with your actual video URLs
]

# Set up base download options
base_ytdl_opts = {
    "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best",
    "outtmpl": "/Volumes/2TB_MAINDISK_FAN_XIANG/DownLoadYoutubeVideos/%(uploader)s/%(upload_date)s-%(title)s.%(ext)s",
    "proxy": None,
    "logger": logging.getLogger(),
    "progress_hooks": [
        lambda d: logging.info(f"Status: {d['status']}, File: {d.get('filename', 'N/A')}")
    ],
    "http_headers": {
        "Authorization": f"Bearer {access_token}"  # Pass the OAuth token in the headers
    }
}

# Download function with retry logic
def download_video(url, attempts=3):
    with yt_dlp.YoutubeDL(base_ytdl_opts) as ydl:
        for attempt in range(attempts):
            try:
                info_dict = ydl.extract_info(url, download=False)  # Get video info only
                # Adjust format for shorter videos
                if info_dict["duration"] < 600:  # Duration in seconds
                    ydl.params["format"] = "best"
                # Perform the actual download
                ydl.download([url])
                logging.info(f"Download completed for {url}")
                print(f"Download completed for {url}")
                break  # Exit loop if download is successful
            except Exception as e:
                logging.error(f"Error downloading {url}: {e}")
                if attempt < attempts - 1:
                    time.sleep(5)  # Wait before retrying
                else:
                    logging.error(f"Failed to download {url} after {attempts} attempts.")

# Execute downloads for all URLs
for url in urls:
    download_video(url)

# Delete log file after successful downloads
if os.path.exists('yt_dlp_download.log'):
    os.remove('yt_dlp_download.log')
    print("Log file deleted.")