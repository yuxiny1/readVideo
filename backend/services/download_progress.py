import time
from pathlib import Path
from typing import Optional

from backend.core.task_state import append_task_log, update_task_details


def build_download_progress_hook(task_id: str):
    last_update = 0.0
    last_bucket = -10

    def report(progress: dict):
        nonlocal last_update, last_bucket
        status = progress.get("status")
        filename = progress.get("filename") or progress.get("tmpfilename") or ""
        total_bytes = progress.get("total_bytes") or progress.get("total_bytes_estimate")
        downloaded_bytes = progress.get("downloaded_bytes")
        percent = download_percent(downloaded_bytes, total_bytes)
        now = time.monotonic()

        if status == "downloading" and now - last_update >= 0.8:
            last_update = now
            update_task_details(
                task_id,
                download_status="downloading",
                download_filename=Path(filename).name if filename else "",
                download_percent=percent,
                downloaded_bytes=downloaded_bytes,
                download_total_bytes=total_bytes,
                download_speed=progress.get("speed"),
                download_eta=progress.get("eta"),
            )

        if status == "downloading" and percent is not None:
            bucket = int(percent // 10) * 10
            if bucket > last_bucket:
                last_bucket = bucket
                append_task_log(task_id, f"下载进度：{percent:.1f}%。", status="downloading")

        if status == "finished":
            update_task_details(
                task_id,
                download_status="finished",
                download_filename=Path(filename).name if filename else "",
                download_percent=100,
                downloaded_bytes=downloaded_bytes,
                download_total_bytes=total_bytes,
                download_speed=progress.get("speed"),
                download_eta=0,
            )
            append_task_log(task_id, "下载完成，正在准备转录。", status="downloading")

        if status == "retrying":
            attempt = progress.get("retry_attempt")
            limit = progress.get("retry_limit")
            update_task_details(task_id, download_status="retrying")
            append_task_log(
                task_id,
                f"下载连接中断，正在自动重试（第 {attempt}/{limit} 次）。",
                level="warning",
                status="downloading",
            )

    return report


def download_percent(downloaded_bytes: Optional[float], total_bytes: Optional[float]) -> Optional[float]:
    if not downloaded_bytes or not total_bytes:
        return None
    return min(100.0, round((downloaded_bytes / total_bytes) * 100, 1))
