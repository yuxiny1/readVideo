from dataclasses import dataclass
from typing import Any, Optional

import yt_dlp


@dataclass(frozen=True)
class SourceVideo:
    title: str
    url: str
    video_id: str
    uploader: str
    upload_date: str
    duration: Optional[int]


def list_source_updates(source_url: str, limit: int = 10) -> list[SourceVideo]:
    ydl_opts = {
        "extract_flat": "in_playlist",
        "playlistend": max(1, min(limit, 50)),
        "quiet": True,
        "skip_download": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(source_url, download=False)

    entries = info.get("entries") or [info]
    videos = []
    for entry in entries[:limit]:
        if not entry:
            continue
        videos.append(_entry_to_video(entry, info))
    return videos


def _entry_to_video(entry: dict[str, Any], parent: dict[str, Any]) -> SourceVideo:
    video_id = str(entry.get("id") or "")
    return SourceVideo(
        title=str(entry.get("title") or "Untitled video"),
        url=_entry_url(entry, video_id),
        video_id=video_id,
        uploader=str(entry.get("uploader") or parent.get("uploader") or parent.get("channel") or ""),
        upload_date=str(entry.get("upload_date") or ""),
        duration=entry.get("duration"),
    )


def _entry_url(entry: dict[str, Any], video_id: str) -> str:
    for key in ("webpage_url", "url"):
        value = str(entry.get(key) or "")
        if value.startswith("http://") or value.startswith("https://"):
            return value
    if video_id:
        return f"https://www.youtube.com/watch?v={video_id}"
    return str(entry.get("url") or "")
