import {Injectable} from "@angular/core";

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
  TaskRecord,
  TranscriptionModelsResponse,
  WatchItem,
  WhisperModelDownloadResponse,
} from "../types/readvideo.types";

@Injectable({providedIn: "root"})
export class ReadvideoApiService {
  async health(): Promise<HealthResponse> {
    return this.request<HealthResponse>("/health");
  }

  async appConfig(): Promise<AppConfig> {
    return this.request<AppConfig>("/app_config");
  }

  async ollamaModels(): Promise<OllamaModelsResponse> {
    return this.request<OllamaModelsResponse>("/api/ollama/models");
  }

  async transcriptionModels(): Promise<TranscriptionModelsResponse> {
    return this.request<TranscriptionModelsResponse>("/api/transcription/models");
  }

  async downloadTranscriptionModel(model: string): Promise<WhisperModelDownloadResponse> {
    return this.request<WhisperModelDownloadResponse>("/api/transcription/models/download", {
      method: "POST",
      body: JSON.stringify({model}),
    });
  }

  async lookupHistory(url: string): Promise<DuplicateLookup> {
    return this.request<DuplicateLookup>(`/api/history/lookup?url=${encodeURIComponent(url)}`);
  }

  async processVideo(payload: ProcessPayload): Promise<TaskRecord> {
    return this.request<TaskRecord>("/process_video/", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  async taskStatus(taskId: string): Promise<TaskRecord> {
    return this.request<TaskRecord>(`/task_status/${encodeURIComponent(taskId)}`);
  }

  async tasks(): Promise<TaskRecord[]> {
    return this.request<TaskRecord[]>("/tasks");
  }

  async history(): Promise<TaskRecord[]> {
    return this.request<TaskRecord[]>("/api/history");
  }

  async favoriteTask(taskId: string): Promise<unknown> {
    return this.request("/api/favorites", {
      method: "POST",
      body: JSON.stringify({task_id: taskId}),
    });
  }

  async favorites(): Promise<FavoriteSummary[]> {
    return this.request<FavoriteSummary[]>("/api/favorites");
  }

  async favoriteFolders(): Promise<FavoriteFolder[]> {
    return this.request<FavoriteFolder[]>("/api/favorites/folders");
  }

  async addFavoriteFolder(name: string, notes: string): Promise<FavoriteFolder> {
    return this.request<FavoriteFolder>("/api/favorites/folders", {
      method: "POST",
      body: JSON.stringify({name, notes}),
    });
  }

  async deleteFavoriteFolder(folderId: number): Promise<unknown> {
    return this.request(`/api/favorites/folders/${encodeURIComponent(folderId)}`, {method: "DELETE"});
  }

  async assignFavoriteFolder(itemId: number, folderId: number | null): Promise<FavoriteSummary> {
    return this.request<FavoriteSummary>(`/api/favorites/${encodeURIComponent(itemId)}/folder`, {
      method: "PATCH",
      body: JSON.stringify({folder_id: folderId}),
    });
  }

  async deleteFavorite(itemId: number): Promise<unknown> {
    return this.request(`/api/favorites/${encodeURIComponent(itemId)}`, {method: "DELETE"});
  }

  async favoriteMarkdown(itemId: number): Promise<MarkdownDocument> {
    return this.request<MarkdownDocument>(`/api/favorites/${encodeURIComponent(itemId)}/markdown`);
  }

  async markdownFiles(directory: string): Promise<MarkdownFile[]> {
    return this.request<MarkdownFile[]>(`/api/markdown_files?directory=${encodeURIComponent(directory)}`);
  }

  async markdownDocument(path: string): Promise<MarkdownDocument> {
    return this.request<MarkdownDocument>(`/api/markdown_files/read?path=${encodeURIComponent(path)}`);
  }

  async watchlist(): Promise<WatchItem[]> {
    return this.request<WatchItem[]>("/watchlist");
  }

  async addWatchItem(item: Pick<WatchItem, "name" | "url" | "notes">): Promise<WatchItem> {
    return this.request<WatchItem>("/watchlist", {
      method: "POST",
      body: JSON.stringify(item),
    });
  }

  async reorderWatchItems(itemIds: number[]): Promise<WatchItem[]> {
    return this.request<WatchItem[]>("/watchlist/reorder", {
      method: "PATCH",
      body: JSON.stringify({item_ids: itemIds}),
    });
  }

  async deleteWatchItem(id: number): Promise<unknown> {
    return this.request(`/watchlist/${encodeURIComponent(id)}`, {method: "DELETE"});
  }

  async sourceUpdates(id: number, limit = 8): Promise<SourceUpdatesResponse> {
    return this.request<SourceUpdatesResponse>(`/watchlist/${encodeURIComponent(id)}/updates?limit=${limit}`);
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const response = await fetch(path, {
      headers: {"Content-Type": "application/json", ...(options.headers || {})},
      ...options,
    });
    const text = await response.text();
    const data = text ? JSON.parse(text) : null;
    if (!response.ok) {
      throw new Error(data?.detail || data?.error || response.statusText);
    }
    return data as T;
  }
}
