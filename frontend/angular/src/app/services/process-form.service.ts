import {Injectable, signal} from "@angular/core";

import {ProcessPayload} from "../types/readvideo.types";

export interface ProcessFormState {
  url: string;
  notesDir: string;
  transcriptionBackend: "local" | "openai";
  transcriptionModel: string;
  localWhisperModel: string;
  localWhisperLanguage: string;
  notesBackend: "extractive" | "ollama";
  ollamaModel: string;
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
  });

  patch(update: Partial<ProcessFormState>): void {
    this.form.update((form) => ({...form, ...update}));
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
    };
  }
}
