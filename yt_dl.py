# yt_dl.py

import yt_dlp
import logging
import os

def download_video(url: str, access_token: str, download_path: str):
    logging.basicConfig(filename='yt_dlp_download.log', level=logging.INFO)
    # Set up the download options for yt-dlp
    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best",  # Prefer mp4 and m4a formats
        "outtmpl": os.path.join(download_path, "%(title)s.%(ext)s"),  # Set the output template
        "logger": logging.getLogger(),
        "progress_hooks": [lambda d: logging.info(f"Progress: {d['status']}")],
        "http_headers": {
            "Authorization": f"Bearer {access_token}"  # Pass the OAuth token in the headers
        }
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info_dict = ydl.extract_info(url, download=False)  # Get video info only
            if info_dict["duration"] < 600:  # Duration in seconds
                ydl.params["format"] = "best"
            ydl.download([url])
            logging.info(f"Download completed for {url}")
            print(f"Download completed for {url}")
        except Exception as e:
            logging.error(f"Error downloading {url}: {e}")
            print(f"Error downloading {url}: {e}")
