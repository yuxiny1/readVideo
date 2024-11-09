import yt_dlp
import logging
import os

def download_video(url: str, access_token: str, download_path: str) -> str:
    logging.basicConfig(filename='yt_dlp_download.log', level=logging.INFO)
    
    # Set up the download options for yt-dlp
    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best",  # Prefer mp4 and m4a formats
        "outtmpl": os.path.join(download_path, "%(uploader)s/%(upload_date)s-%(title)s.%(ext)s"),  # Set the output template
        "logger": logging.getLogger(),
        "progress_hooks": [lambda d: logging.info(f"Progress: {d['status']}")],
        "http_headers": {
            "Authorization": f"Bearer {access_token}"  # Pass the OAuth token in the headers
        }
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # Extract video info without downloading
            info_dict = ydl.extract_info(url, download=False)
            video_title = info_dict.get("title", "Unknown Video Title")
            output_file = os.path.join(download_path, f"{video_title}.mp4")  # Expected file name with .mp4 extension

            # Ensure directory exists
            if not os.path.exists(os.path.dirname(output_file)):
                os.makedirs(os.path.dirname(output_file))

            # Check if the video already exists
            if os.path.exists(output_file):
                logging.info(f"Video {video_title} already exists, skipping download.")
                print(f"Video {video_title} already exists, skipping download.")
                return output_file  # Return the file path even if it exists

            # Download the video
            ydl.download([url])
            logging.info(f"Download completed for {url}")
            print(f"Download completed for {url}")
            
            return output_file  # Return the file path after downloading

        except Exception as e:
            logging.error(f"Error downloading {url}: {e}")
            print(f"Error downloading {url}: {e}")
            return None  # Return None in case of error