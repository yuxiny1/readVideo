import {HttpClient, HttpErrorResponse} from "@angular/common/http";
import {Injectable, inject} from "@angular/core";
import {Observable, catchError, throwError} from "rxjs";

import {
  AppConfig,
  DuplicateLookup,
  FavoriteFolder,
  FavoriteSummary,
  HealthResponse,
  MarkdownDocument,
  MarkdownFile,
  OllamaModelsResponse,
  ProcessPayload,
  SourceUpdatesResponse,
  TagSummary,
  TaskRecord,
  TranscriptionModelsResponse,
  WatchItem,
  WhisperModelDownloadResponse,
} from "../../../shared/models/readvideo-types/readvideo.types";

interface ApiErrorPayload {
  detail?: string;
  error?: string;
}

@Injectable({providedIn: "root"})
export class ReadvideoApiService {
  private readonly http = inject(HttpClient);

  health(): Observable<HealthResponse> {
    return this.get<HealthResponse>("/health");
  }

  appConfig(): Observable<AppConfig> {
    return this.get<AppConfig>("/app_config");
  }

  ollamaModels(): Observable<OllamaModelsResponse> {
    return this.get<OllamaModelsResponse>("/api/ollama/models");
  }

  transcriptionModels(): Observable<TranscriptionModelsResponse> {
    return this.get<TranscriptionModelsResponse>("/api/transcription/models");
  }

  downloadTranscriptionModel(model: string): Observable<WhisperModelDownloadResponse> {
    return this.post<WhisperModelDownloadResponse>("/api/transcription/models/download", {model});
  }

  lookupHistory(url: string): Observable<DuplicateLookup> {
    return this.get<DuplicateLookup>(`/api/history/lookup?url=${encodeURIComponent(url)}`);
  }

  processVideo(payload: ProcessPayload): Observable<TaskRecord> {
    return this.post<TaskRecord>("/process_video/", payload);
  }

  taskStatus(taskId: string): Observable<TaskRecord> {
    return this.get<TaskRecord>(`/task_status/${encodeURIComponent(taskId)}`);
  }

  tasks(): Observable<TaskRecord[]> {
    return this.get<TaskRecord[]>("/tasks");
  }

  history(): Observable<TaskRecord[]> {
    return this.get<TaskRecord[]>("/api/history");
  }

  tags(): Observable<TagSummary[]> {
    return this.get<TagSummary[]>("/api/tags");
  }

  updateHistoryTags(taskId: string, tags: string[]): Observable<TaskRecord> {
    return this.patch<TaskRecord>(`/api/history/${encodeURIComponent(taskId)}/tags`, {tags});
  }

  favoriteTask(taskId: string): Observable<unknown> {
    return this.post<unknown>("/api/favorites", {task_id: taskId});
  }

  favorites(): Observable<FavoriteSummary[]> {
    return this.get<FavoriteSummary[]>("/api/favorites");
  }

  favoriteFolders(): Observable<FavoriteFolder[]> {
    return this.get<FavoriteFolder[]>("/api/favorites/folders");
  }

  addFavoriteFolder(name: string, notes: string): Observable<FavoriteFolder> {
    return this.post<FavoriteFolder>("/api/favorites/folders", {name, notes});
  }

  updateFavoriteFolder(folderId: number, name: string, notes: string): Observable<FavoriteFolder> {
    return this.patch<FavoriteFolder>(`/api/favorites/folders/${encodeURIComponent(folderId)}`, {name, notes});
  }

  deleteFavoriteFolder(folderId: number): Observable<unknown> {
    return this.delete<unknown>(`/api/favorites/folders/${encodeURIComponent(folderId)}`);
  }

  assignFavoriteFolder(itemId: number, folderId: number | null): Observable<FavoriteSummary> {
    return this.patch<FavoriteSummary>(`/api/favorites/${encodeURIComponent(itemId)}/folder`, {folder_id: folderId});
  }

  updateFavoriteTags(itemId: number, tags: string[]): Observable<FavoriteSummary> {
    return this.patch<FavoriteSummary>(`/api/favorites/${encodeURIComponent(itemId)}/tags`, {tags});
  }

  deleteFavorite(itemId: number): Observable<unknown> {
    return this.delete<unknown>(`/api/favorites/${encodeURIComponent(itemId)}`);
  }

  favoriteMarkdown(itemId: number): Observable<MarkdownDocument> {
    return this.get<MarkdownDocument>(`/api/favorites/${encodeURIComponent(itemId)}/markdown`);
  }

  markdownFiles(directory: string): Observable<MarkdownFile[]> {
    return this.get<MarkdownFile[]>(`/api/markdown_files?directory=${encodeURIComponent(directory)}`);
  }

  markdownDocument(path: string): Observable<MarkdownDocument> {
    return this.get<MarkdownDocument>(`/api/markdown_files/read?path=${encodeURIComponent(path)}`);
  }

  watchlist(): Observable<WatchItem[]> {
    return this.get<WatchItem[]>("/watchlist");
  }

  addWatchItem(item: Pick<WatchItem, "name" | "url" | "notes">): Observable<WatchItem> {
    return this.post<WatchItem>("/watchlist", item);
  }

  reorderWatchItems(itemIds: number[]): Observable<WatchItem[]> {
    return this.patch<WatchItem[]>("/watchlist/reorder", {item_ids: itemIds});
  }

  deleteWatchItem(id: number): Observable<unknown> {
    return this.delete<unknown>(`/watchlist/${encodeURIComponent(id)}`);
  }

  sourceUpdates(id: number, limit = 8): Observable<SourceUpdatesResponse> {
    return this.get<SourceUpdatesResponse>(`/watchlist/${encodeURIComponent(id)}/updates?limit=${limit}`);
  }

  private get<T>(path: string): Observable<T> {
    return this.handle(this.http.get<T>(path));
  }

  private post<T>(path: string, body: unknown): Observable<T> {
    return this.handle(this.http.post<T>(path, body));
  }

  private patch<T>(path: string, body: unknown): Observable<T> {
    return this.handle(this.http.patch<T>(path, body));
  }

  private delete<T>(path: string): Observable<T> {
    return this.handle(this.http.delete<T>(path));
  }

  private handle<T>(request$: Observable<T>): Observable<T> {
    return request$.pipe(
      catchError((error: HttpErrorResponse) => throwError(() => new Error(apiErrorMessage(error)))),
    );
  }
}

function apiErrorMessage(error: HttpErrorResponse): string {
  if (typeof error.error === "string" && error.error.trim()) {
    return error.error;
  }
  const payload = error.error as ApiErrorPayload | null;
  return payload?.detail || payload?.error || error.message || `Request failed (${error.status})`;
}
