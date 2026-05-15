from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from backend.storage.history import HistoryRecord, HistoryStore


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class HistoryReuseCandidate:
    record: HistoryRecord
    video_path: Optional[Path]
    transcript_path: Optional[Path]
    markdown_path: Optional[Path]

    @property
    def video_exists(self) -> bool:
        return self.video_path is not None

    @property
    def transcript_exists(self) -> bool:
        return self.transcript_path is not None

    @property
    def markdown_exists(self) -> bool:
        return self.markdown_path is not None

    @property
    def can_reuse(self) -> bool:
        return self.video_exists


def find_history_reuse_candidate(
    database_path: str,
    url: str,
    download_dir: str,
    task_id: Optional[str] = None,
) -> Optional[HistoryReuseCandidate]:
    store = HistoryStore(database_path)
    record = store.get_record(task_id) if task_id else store.find_latest_by_url(url)
    if record is None:
        return None

    video_path = resolve_existing_path(record.video_path, download_dir)
    transcript_path = resolve_existing_path(record.transcription_path)
    markdown_path = resolve_existing_path(record.markdown_path)
    return HistoryReuseCandidate(
        record=record,
        video_path=video_path,
        transcript_path=transcript_path,
        markdown_path=markdown_path,
    )


def resolve_existing_path(path: str, fallback_dir: Optional[str] = None) -> Optional[Path]:
    if not path:
        return None

    candidates = []
    raw_path = Path(path).expanduser()
    candidates.append(raw_path if raw_path.is_absolute() else PROJECT_ROOT / raw_path)

    if fallback_dir:
        fallback_path = Path(fallback_dir).expanduser()
        fallback_base = fallback_path if fallback_path.is_absolute() else PROJECT_ROOT / fallback_path
        candidates.append(fallback_base / raw_path.name)

    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None
