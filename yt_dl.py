import yt_dlp
import logging
import os

def download_video(url: str, access_token: str, download_path: str) -> str:
    logging.basicConfig(filename='yt_dlp_download.log', level=logging.INFO)
    
    # Ensure the download directory exists
    os.makedirs(download_path, exist_ok=True)
    
    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best",
        "outtmpl": os.path.join(download_path, "%(title)s.%(ext)s"),  # Filename template for yt-dlp
        "logger": logging.getLogger(),
        "progress_hooks": [lambda d: logging.info(f"Progress: {d['status']}")],
        "http_headers": {
            "Authorization": f"Bearer {access_token}"
        }
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info_dict = ydl.extract_info(url, download=False)
            video_title = info_dict.get("title", "Unknown Video Title")
            
            # Expected file path
            expected_output_file = os.path.join(download_path, f"{video_title}.mp4")
            
            # Download the video
            ydl.download([url])
            logging.info(f"Download completed for {url}")
            print(f"Download completed for {url}")
            
            # Check if the expected file exists
            if os.path.isfile(expected_output_file):
                return expected_output_file
            else:
                # If the file is missing, search for any MP4 files in the directory
                for file in os.listdir(download_path):
                    if file.endswith(".mp4") and video_title in file:
                        return os.path.join(download_path, file)
                
                logging.error("Download completed but file not found at expected path")
                return None

        except Exception as e:
            logging.error(f"Error downloading {url}: {e}")
            print(f"Error downloading {url}: {e}")
            return None