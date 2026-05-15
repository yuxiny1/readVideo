import logging
import os
from pathlib import Path
from typing import Callable, Optional

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


def download_video(
    url: str,
    download_path: str = "downloads/youtube_videos",
    progress_hook: Optional[Callable[[dict], None]] = None,
) -> str:
    """Download a video with yt-dlp and return the path to the downloaded file."""
    logging.basicConfig(filename="yt_dlp_download.log", level=logging.INFO)

    output_dir = Path(download_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    files_before_download = {path.resolve() for path in output_dir.iterdir() if path.is_file()}

    progress_hooks = [lambda d: logger.info("yt-dlp progress: %s", d.get("status"))]
    if progress_hook is not None:
        progress_hooks.append(progress_hook)

    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best",
        "merge_output_format": "mp4",
        "outtmpl": str(output_dir / "%(title).200s.%(ext)s"),
        "logger": logging.getLogger(),
        "progress_hooks": progress_hooks,
        "noplaylist": True,
    }

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
