import {Injectable, signal} from "@angular/core";

import {ProcessPayload} from "../types/readvideo.types";

const DELETE_VIDEO_AFTER_COMPLETION_KEY = "readvideo.deleteVideoAfterCompletion";

export interface ProcessFormState {
  url: string;
  notesDir: string;
  transcriptionBackend: "local" | "openai";
  transcriptionModel: string;
  localWhisperModel: string;
  localWhisperLanguage: string;
  notesBackend: "extractive" | "ollama";
  ollamaModel: string;
  deleteVideoAfterCompletion: boolean;
}

@Injectable({providedIn: "root"})
export class ProcessFormService {
  readonly form = signal<ProcessFormState>({
    url: "",
    notesDir: "",
    transcriptionBackend: "local",
    transcriptionModel: "",
    localWhisperModel: "",
    localWhisperLanguage: "",
    notesBackend: "extractive",
    ollamaModel: "",
    deleteVideoAfterCompletion: readDeleteVideoDefault(),
  });

  patch(update: Partial<ProcessFormState>): void {
    this.form.update((form) => ({...form, ...update}));
    if (typeof update.deleteVideoAfterCompletion === "boolean") {
      writeDeleteVideoDefault(update.deleteVideoAfterCompletion);
    }
  }

  payload(url: string, options: {reuseTaskId?: string; forceDownload?: boolean} = {}): ProcessPayload {
    const form = this.form();
    return {
      url,
      notes_dir: form.notesDir.trim() || null,
      transcription_backend: form.transcriptionBackend,
      transcription_model: form.transcriptionModel.trim() || null,
      local_whisper_model: form.localWhisperModel.trim() || null,
      local_whisper_language: form.localWhisperLanguage.trim() || null,
      notes_backend: form.notesBackend,
      ollama_model: form.ollamaModel.trim() || null,
      reuse_task_id: options.reuseTaskId || null,
      force_download: Boolean(options.forceDownload),
      delete_video_after_completion: form.deleteVideoAfterCompletion,
    };
  }
}

function readDeleteVideoDefault(): boolean {
  try {
    return typeof localStorage !== "undefined" && localStorage.getItem(DELETE_VIDEO_AFTER_COMPLETION_KEY) === "true";
  } catch {
    return false;
  }
}

function writeDeleteVideoDefault(value: boolean): void {
  try {
    if (typeof localStorage !== "undefined") {
      localStorage.setItem(DELETE_VIDEO_AFTER_COMPLETION_KEY, value ? "true" : "false");
    }
  } catch {
    // Browsers can block storage in private modes; the in-memory setting still works for this run.
  }
}
