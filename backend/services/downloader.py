import logging
import os
import re
from pathlib import Path
from typing import Callable, Optional

import yt_dlp


logger = logging.getLogger(__name__)
DOWNLOAD_RETRIES = 20
HTTP_CHUNK_SIZE = 10 * 1024 * 1024


class YtDlpLogger:
    def __init__(self, progress_hook: Optional[Callable[[dict], None]] = None):
        self.name = logger.name
        self._progress_hook = progress_hook

    def debug(self, message: str) -> None:
        logger.debug("%s", message)
        self._report_retry(message)

    def info(self, message: str) -> None:
        logger.info("%s", message)

    def warning(self, message: str) -> None:
        logger.warning("%s", message)
        self._report_retry(message)

    def _report_retry(self, message: str) -> None:
        retry = re.search(r"Retrying.*\((\d+)/(\d+)\)", message)
        if retry and self._progress_hook is not None:
            self._progress_hook({
                "status": "retrying",
                "retry_attempt": int(retry.group(1)),
                "retry_limit": int(retry.group(2)),
            })

    def error(self, message: str) -> None:
        logger.error("%s", message)


def _retry_delay(n: int) -> int:
    return min(2 ** n, 10)


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
    logger.info("已将下载文件名从 %s 规范为 %s", source, candidate)
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
    output_dir = Path(download_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    files_before_download = {path.resolve() for path in output_dir.iterdir() if path.is_file()}

    progress_hooks = [lambda d: logger.info("yt-dlp 进度：%s", d.get("status"))]
    if progress_hook is not None:
        progress_hooks.append(progress_hook)

    # YoutubeDL's Python API does not inherit the CLI retry defaults.
    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best",
        "merge_output_format": "mp4",
        "outtmpl": str(output_dir / "%(title).200s.%(ext)s"),
        "logger": YtDlpLogger(progress_hook),
        "progress_hooks": progress_hooks,
        "noplaylist": True,
        "retries": DOWNLOAD_RETRIES,
        "fragment_retries": DOWNLOAD_RETRIES,
        "file_access_retries": 5,
        "extractor_retries": 5,
        "retry_sleep_functions": {
            "http": _retry_delay,
            "fragment": _retry_delay,
        },
        "continuedl": True,
        "nopart": False,
        "http_chunk_size": HTTP_CHUNK_SIZE,
        "socket_timeout": 30,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info_dict = ydl.extract_info(url, download=True)
            downloaded_file = _downloaded_file_from_info(info_dict)
            if downloaded_file:
                downloaded_file = normalize_downloaded_file_path(downloaded_file)
                logger.info("%s 下载完成：%s", url, downloaded_file)
                return downloaded_file

            prepared = ydl.prepare_filename(info_dict)
            candidates = [
                prepared,
                str(Path(prepared).with_suffix(".mp4")),
            ]
            for candidate in candidates:
                if os.path.isfile(candidate):
                    candidate = normalize_downloaded_file_path(candidate)
                    logger.info("%s 下载完成：%s", url, candidate)
                    return candidate

            files_after_download = {path.resolve() for path in output_dir.iterdir() if path.is_file()}
            new_files = sorted(
                files_after_download - files_before_download,
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )
            if new_files:
                downloaded_file = normalize_downloaded_file_path(str(new_files[0]))
                logger.info("%s 下载完成：%s", url, downloaded_file)
                return downloaded_file

            raise FileNotFoundError("yt-dlp 已完成，但没有找到下载后的视频文件。")
        except Exception:
            logger.exception("下载 %s 时发生错误", url)
            raise
