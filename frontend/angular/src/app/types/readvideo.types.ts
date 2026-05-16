export type NoticeKind = "muted" | "pending" | "ok" | "error";

export interface NoticeState {
  text: string;
  kind: NoticeKind;
}

export interface HealthResponse {
  status: string;
}

export interface AppConfig {
  transcription_backend: "local" | "openai";
  download_dir: string;
  notes_dir: string;
  notes_backend: "extractive" | "ollama";
  ollama_model: string;
  local_whisper_model: string;
  local_whisper_language: string;
  transcription_model: string;
}

export interface OllamaModel {
  name: string;
  size: number;
  size_label: string;
  modified_at: string;
  family: string;
  parameter_size: string;
  quantization_level: string;
}

export interface OllamaModelsResponse {
  status: "ok" | "error";
  default_model: string;
  error?: string;
  models: OllamaModel[];
}

export interface WhisperModelOption {
  name: string;
  label: string;
  size: string;
  path: string;
  url: string;
  notes: string;
  installed: boolean;
  recommended: boolean;
}

export interface TranscriptionLanguageOption {
  code: string;
  label: string;
}

export interface TranscriptionModelsResponse {
  whisper: WhisperModelOption[];
  installed_whisper: string[];
  openai: Array<{name: string; label: string; notes: string}>;
  languages: TranscriptionLanguageOption[];
}

export interface WhisperModelDownloadResponse {
  model: string;
  path: string;
  downloaded: boolean;
}

export interface TaskLog {
  time: string;
  level: NoticeKind | "info";
  status: string;
  message: string;
}

export interface TaskRecord {
  task_id: string;
  status: string;
  url?: string;
  title?: string;
  video_path?: string;
  transcription_path?: string;
  markdown_path?: string;
  summary?: string;
  error?: string;
  transcription_backend?: string;
  summary_backend?: string;
  notes_backend?: string;
  ollama_model?: string;
  created_at?: string;
  updated_at?: string;
  completed_at?: string;
  logs?: TaskLog[];
  download_status?: string;
  download_filename?: string;
  download_percent?: number;
  downloaded_bytes?: number;
  download_total_bytes?: number;
  download_speed?: number;
  download_eta?: number;
  delete_video_after_completion?: boolean;
  video_deleted_after_completion?: boolean;
  video_delete_error?: string;
}

export interface ProcessPayload {
  url: string;
  notes_dir: string | null;
  transcription_backend: "local" | "openai";
  transcription_model: string | null;
  local_whisper_model: string | null;
  local_whisper_language: string | null;
  notes_backend: "extractive" | "ollama";
  ollama_model: string | null;
  reuse_task_id?: string | null;
  force_download?: boolean;
  delete_video_after_completion?: boolean;
}

export interface DuplicateLookup {
  found: boolean;
  can_reuse: boolean;
  video_exists?: boolean;
  transcript_exists?: boolean;
  markdown_exists?: boolean;
  record?: TaskRecord;
  resolved_paths?: {
    video?: string;
    transcript?: string;
    markdown?: string;
  };
}

export interface WatchItem {
  id: number;
  name: string;
  url: string;
  notes: string;
  created_at?: string;
}

export interface SourceUpdate {
  title: string;
  url: string;
  video_id: string;
  uploader?: string;
  upload_date?: string;
  duration?: number;
}

export interface SourceUpdatesResponse {
  source: WatchItem;
  updates: SourceUpdate[];
}

export interface FavoriteFolder {
  id: number;
  name: string;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface FavoriteSummary {
  id: number;
  task_id: string;
  folder_id: number | null;
  folder_name: string;
  title: string;
  url: string;
  summary: string;
  markdown_path: string;
  notes_dir: string;
  created_at: string;
  updated_at: string;
}

export interface MarkdownFile {
  name: string;
  path: string;
  size_bytes: number;
  modified_at: string;
}

export interface MarkdownDocument {
  path: string;
  content: string;
}
