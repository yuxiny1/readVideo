import logging
import os
from pathlib import Path
from typing import Optional

import yt_dlp


logger = logging.getLogger(__name__)


def _downloaded_file_from_info(info_dict: dict) -> Optional[str]:
    """Best-effort extraction of the final media path from yt-dlp metadata."""
    requested_downloads = info_dict.get("requested_downloads") or []
    for download in requested_downloads:
        filepath = download.get("filepath") or download.get("_filename")
        if filepath and os.path.exists(filepath):
            return filepath

    filepath = info_dict.get("filepath") or info_dict.get("_filename")
    if filepath and os.path.exists(filepath):
        return filepath

    return None


def _build_ydl_options(output_dir: Path, media_type: str = "audio") -> dict:
    media_type = media_type.lower()
    if media_type == "audio":
        format_selector = "bestaudio[ext=m4a]/bestaudio/best"
        merge_output_format = None
    elif media_type == "video":
        format_selector = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best"
        merge_output_format = "mp4"
    else:
        raise ValueError("media_type must be audio or video")

    options = {
        "format": format_selector,
        "outtmpl": str(output_dir / "%(title).200s.%(ext)s"),
        "logger": logging.getLogger(),
        "progress_hooks": [lambda d: logger.info("yt-dlp progress: %s", d.get("status"))],
        "noplaylist": True,
    }
    if merge_output_format:
        options["merge_output_format"] = merge_output_format
    return options


def download_media(url: str, download_path: str = "downloads/youtube_videos", media_type: str = "audio") -> str:
    """Download audio or video with yt-dlp and return the path to the local media file."""
    logging.basicConfig(filename="yt_dlp_download.log", level=logging.INFO)

    output_dir = Path(download_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    files_before_download = {path.resolve() for path in output_dir.iterdir() if path.is_file()}

    ydl_opts = _build_ydl_options(output_dir, media_type)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info_dict = ydl.extract_info(url, download=True)
            downloaded_file = _downloaded_file_from_info(info_dict)
            if downloaded_file:
                logger.info("Download completed for %s: %s", url, downloaded_file)
                return downloaded_file

            prepared = ydl.prepare_filename(info_dict)
            candidates = [
                prepared,
                str(Path(prepared).with_suffix(".mp4")),
                str(Path(prepared).with_suffix(".m4a")),
                str(Path(prepared).with_suffix(".webm")),
                str(Path(prepared).with_suffix(".opus")),
            ]
            for candidate in candidates:
                if os.path.isfile(candidate):
                    logger.info("Download completed for %s: %s", url, candidate)
                    return candidate

            files_after_download = {path.resolve() for path in output_dir.iterdir() if path.is_file()}
            new_files = sorted(
                files_after_download - files_before_download,
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )
            if new_files:
                logger.info("Download completed for %s: %s", url, new_files[0])
                return str(new_files[0])

            raise FileNotFoundError("yt-dlp finished but the downloaded file could not be found")
        except Exception:
            logger.exception("Error downloading %s", url)
            raise


def download_video(url: str, download_path: str = "downloads/youtube_videos") -> str:
    """Compatibility wrapper for older callers that expected video downloads."""
    return download_media(url, download_path, media_type="video")
