import logging
import os
import re
from pathlib import Path
from typing import Callable, Optional

import yt_dlp


logger = logging.getLogger(__name__)


def clean_filename_part(value: str) -> str:
    cleaned = value.replace("\u3000", " ")
    cleaned = re.sub(r"[\u200b-\u200f\u202a-\u202e\ufeff]", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", cleaned)
    cleaned = cleaned.strip(" .")
    return cleaned or "video"


def normalize_downloaded_file_path(path: str) -> str:
    source = Path(path)
    cleaned_name = f"{clean_filename_part(source.stem)}{source.suffix.lower()}"
    target = source.with_name(cleaned_name)
    if target == source:
        return str(source)

    candidate = target
    counter = 2
    while candidate.exists():
        try:
            if source.samefile(candidate):
                break
        except OSError:
            pass
        candidate = target.with_name(f"{target.stem} {counter}{target.suffix}")
        counter += 1

    source.rename(candidate)
    logger.info("Normalized downloaded filename from %s to %s", source, candidate)
    return str(candidate)


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
                downloaded_file = normalize_downloaded_file_path(downloaded_file)
                logger.info("Download completed for %s: %s", url, downloaded_file)
                return downloaded_file

            prepared = ydl.prepare_filename(info_dict)
            candidates = [
                prepared,
                str(Path(prepared).with_suffix(".mp4")),
            ]
            for candidate in candidates:
                if os.path.isfile(candidate):
                    candidate = normalize_downloaded_file_path(candidate)
                    logger.info("Download completed for %s: %s", url, candidate)
                    return candidate

            files_after_download = {path.resolve() for path in output_dir.iterdir() if path.is_file()}
            new_files = sorted(
                files_after_download - files_before_download,
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )
            if new_files:
                downloaded_file = normalize_downloaded_file_path(str(new_files[0]))
                logger.info("Download completed for %s: %s", url, downloaded_file)
                return downloaded_file

            raise FileNotFoundError("yt-dlp finished but the downloaded file could not be found")
        except Exception:
            logger.exception("Error downloading %s", url)
            raise
