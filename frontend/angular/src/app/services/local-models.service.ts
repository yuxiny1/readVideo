import {DestroyRef, Injectable, computed, inject, signal} from "@angular/core";
import {takeUntilDestroyed} from "@angular/core/rxjs-interop";
import {map, switchMap, take} from "rxjs";

import {errorMessage} from "../shared/errors";
import {
  AppConfig,
  NoticeState,
  OllamaModel,
  TranscriptionLanguageOption,
  TranscriptionModelsResponse,
  WhisperModelOption,
} from "../types/readvideo.types";
import {ProcessFormService} from "./process-form.service";
import {ReadvideoApiService} from "./readvideo-api.service";

@Injectable()
export class LocalModelsService {
  private readonly api = inject(ReadvideoApiService);
  private readonly form = inject(ProcessFormService);
  private readonly destroyRef = inject(DestroyRef);

  readonly config = signal<AppConfig | null>(null);
  readonly ollamaModels = signal<OllamaModel[]>([]);
  readonly ollamaAvailable = signal(false);
  readonly ollamaStatus = signal<NoticeState>({text: "Checking Ollama models...", kind: "muted"});
  readonly whisperModels = signal<WhisperModelOption[]>([]);
  readonly transcriptionLanguages = signal<TranscriptionLanguageOption[]>([]);
  readonly whisperStatus = signal<NoticeState>({text: "Checking local Whisper models...", kind: "muted"});
  readonly ollamaModelOptions = computed(() => [...this.ollamaModels()].sort((first, second) => {
    const sizeDelta = Number(second.size || 0) - Number(first.size || 0);
    return sizeDelta || first.name.localeCompare(second.name);
  }));

  initialize(config: AppConfig): void {
    this.config.set(config);
    this.form.patch({
      transcriptionBackend: config.transcription_backend || "local",
      localWhisperModel: config.local_whisper_model || "models/ggml-large-v3-turbo.bin",
      localWhisperLanguage: config.local_whisper_language || "auto",
      notesBackend: "ollama",
      noteStyle: config.note_style || "detailed",
      ollamaModel: config.ollama_model || "qwen2.5:32b",
    });
    this.loadOllamaModels(true);
    this.loadTranscriptionModels(true);
  }

  loadOllamaModels(preferStrongest = false): void {
    this.api.ollamaModels().pipe(
      take(1),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: (result) => {
        this.ollamaAvailable.set(result.status === "ok");
        this.ollamaModels.set(result.models ?? []);
        if (result.status !== "ok") {
          this.ollamaStatus.set({text: result.error || "Ollama is not reachable.", kind: "error"});
          return;
        }
        this.selectDefaultOllamaModel(preferStrongest);
        this.validateOllamaSelection();
      },
      error: (error) => {
        this.ollamaAvailable.set(false);
        this.ollamaModels.set([]);
        this.ollamaStatus.set({text: errorMessage(error), kind: "error"});
      },
    });
  }

  loadTranscriptionModels(preferStrongest = false): void {
    this.api.transcriptionModels().pipe(
      take(1),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: (result) => this.applyTranscriptionModels(result, preferStrongest),
      error: (error) => {
        this.whisperModels.set([]);
        this.transcriptionLanguages.set([]);
        this.whisperStatus.set({text: errorMessage(error), kind: "error"});
      },
    });
  }

  downloadSelectedWhisperModel(modelPath = this.form.form().localWhisperModel): void {
    const model = this.resolveWhisperModel(modelPath) ?? this.recommendedWhisperModel();
    if (!model) {
      this.whisperStatus.set({text: "Choose a recommended Whisper model before downloading.", kind: "error"});
      return;
    }
    this.whisperStatus.set({text: `Downloading ${model.label} (${model.size})...`, kind: "pending"});
    this.api.downloadTranscriptionModel(model.name).pipe(
      switchMap((download) => this.api.transcriptionModels().pipe(
        map((models) => ({download, models})),
      )),
      take(1),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: ({download, models}) => {
        this.form.patch({localWhisperModel: download.path});
        this.applyTranscriptionModels(models, false);
        this.whisperStatus.set({
          text: download.downloaded
            ? `Ready: downloaded ${model.label}.`
            : `Ready: ${model.label} was already installed.`,
          kind: "ok",
        });
      },
      error: (error) => this.whisperStatus.set({text: errorMessage(error), kind: "error"}),
    });
  }

  validateWhisperSelection(): boolean {
    const selection = this.form.form().localWhisperModel.trim() || this.config()?.local_whisper_model || "";
    const model = this.resolveWhisperModel(selection);
    if (model?.installed) {
      this.whisperStatus.set({
        text: model.recommended
          ? `Ready: ${model.label} is installed. Recommended for reducing repeated transcript text.`
          : `Ready: ${model.label} is installed. Large v3 Turbo is stronger if repeats continue.`,
        kind: model.recommended ? "ok" : "pending",
      });
      return true;
    }
    if (model) {
      this.whisperStatus.set({
        text: `Not installed: ${model.label} (${model.size}). Use Download, or run: curl -L -o ${model.path} ${model.url}`,
        kind: "error",
      });
      return false;
    }
    this.whisperStatus.set({
      text: selection ? `Custom model path: ${selection}` : "Choose a local Whisper model.",
      kind: selection ? "muted" : "error",
    });
    return Boolean(selection);
  }

  validateOllamaSelection(): boolean {
    const selectedName = this.form.form().ollamaModel.trim()
      || this.config()?.ollama_model
      || "qwen2.5:32b";
    if (!this.ollamaAvailable()) {
      this.ollamaStatus.set({text: "Ollama is not reachable.", kind: "error"});
      return false;
    }
    if (!this.isInstalledOllamaModel(selectedName)) {
      this.ollamaStatus.set({text: `Missing: ${selectedName}. Run: ollama pull ${selectedName}`, kind: "error"});
      return false;
    }
    const selected = this.resolveOllamaModel(selectedName);
    const size = selected?.size_label ? ` (${selected.size_label})` : "";
    this.ollamaStatus.set({text: `Ready: ${selectedName}${size} is installed locally.`, kind: "ok"});
    return true;
  }

  recommendedWhisperModel(): WhisperModelOption | null {
    return this.whisperModels().find((model) => model.recommended) ?? this.whisperModels()[0] ?? null;
  }

  resolveWhisperModel(pathOrName: string): WhisperModelOption | null {
    const value = pathOrName.trim();
    if (!value) return null;
    return this.whisperModels().find((model) => model.path === value || model.name === value) ?? null;
  }

  resolveOllamaModel(name: string): OllamaModel | null {
    const value = name.trim();
    if (!value) return null;
    return this.ollamaModels().find((model) => model.name === value) ?? null;
  }

  isInstalledOllamaModel(model: string): boolean {
    return !model || this.installedModels().includes(model);
  }

  installedModels(): string[] {
    return this.ollamaModels().map((model) => model.name).filter(Boolean);
  }

  private applyTranscriptionModels(result: TranscriptionModelsResponse, preferStrongest: boolean): void {
    this.whisperModels.set(result.whisper ?? []);
    this.transcriptionLanguages.set(result.languages ?? []);
    const recommended = this.recommendedWhisperModel();
    if (recommended && (preferStrongest || !this.form.form().localWhisperModel.trim())) {
      this.form.patch({localWhisperModel: recommended.path});
    }
    this.validateWhisperSelection();
  }

  private selectDefaultOllamaModel(preferStrongest: boolean): void {
    const strongest = this.ollamaModelOptions()[0];
    if (!strongest) return;
    const current = this.form.form().ollamaModel.trim();
    if (preferStrongest || !current || !this.isInstalledOllamaModel(current)) {
      this.form.patch({ollamaModel: strongest.name});
    }
  }
}
