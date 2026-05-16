import {Injectable, computed, inject, signal} from "@angular/core";

import {formatBytes, formatElapsed, formatEta, formatSpeed, statusLabel} from "../shared/format";
import {
  AppConfig,
  DuplicateLookup,
  NoticeKind,
  NoticeState,
  OllamaModel,
  TaskLog,
  TaskRecord,
  TranscriptionLanguageOption,
  WhisperModelOption,
} from "../types/readvideo.types";
import {ProcessFormService} from "./process-form.service";
import {ReadvideoApiService} from "./readvideo-api.service";

@Injectable({providedIn: "root"})
export class TaskWorkflowService {
  private readonly api = inject(ReadvideoApiService);
  private readonly processForm = inject(ProcessFormService);
  private pollTimer: number | null = null;

  readonly config = signal<AppConfig | null>(null);
  readonly health = signal<"Checking" | "Online" | "Offline">("Checking");
  readonly ollamaModels = signal<OllamaModel[]>([]);
  readonly ollamaAvailable = signal(false);
  readonly ollamaStatus = signal<NoticeState>({text: "Checking Ollama models...", kind: "muted"});
  readonly whisperModels = signal<WhisperModelOption[]>([]);
  readonly transcriptionLanguages = signal<TranscriptionLanguageOption[]>([]);
  readonly whisperStatus = signal<NoticeState>({text: "Checking local Whisper models...", kind: "muted"});
  readonly latestTask = signal<TaskRecord | null>(null);
  readonly latestSummary = signal("");
  readonly notice = signal<NoticeState>({text: "Idle", kind: "muted"});
  readonly duplicate = signal<DuplicateLookup | null>(null);
  readonly duplicateUrl = signal("");
  readonly recentTasks = signal<TaskRecord[]>([]);

  readonly backendLabel = computed(() => {
    const config = this.config();
    return config ? `${config.transcription_backend} / ${config.notes_backend}` : "Backend";
  });

  readonly taskIdLabel = computed(() => {
    const taskId = this.latestTask()?.task_id;
    return taskId ? `Task ${taskId}` : "";
  });

  readonly progressPercent = computed(() => {
    const task = this.latestTask();
    if (!task) return 0;
    if (task.status === "completed") return 100;
    const percent = Number(task.download_percent);
    return Number.isFinite(percent) ? Math.max(0, Math.min(100, percent)) : 0;
  });

  readonly phaseTitle = computed(() => statusLabel(this.latestTask()?.status || "idle"));
  readonly phaseDetail = computed(() => this.describePhase(this.latestTask()));
  readonly logs = computed(() => this.latestTask()?.logs || []);

  async initialize(): Promise<void> {
    try {
      const [health, config] = await Promise.all([this.api.health(), this.api.appConfig()]);
      this.health.set(health.status === "ok" ? "Online" : "Offline");
      this.config.set(config);
      this.processForm.patch({
        transcriptionBackend: config.transcription_backend || "local",
        localWhisperModel: config.local_whisper_model || "models/ggml-large-v3-turbo.bin",
        localWhisperLanguage: config.local_whisper_language || "auto",
        notesBackend: config.notes_backend || "extractive",
      });
      await Promise.all([this.loadOllamaModels(), this.loadTranscriptionModels(), this.loadRecentTasks()]);
    } catch (error) {
      this.health.set("Offline");
      this.setNotice(this.errorMessage(error), "error");
    }
  }

  async loadOllamaModels(): Promise<void> {
    try {
      const result = await this.api.ollamaModels();
      this.ollamaAvailable.set(result.status === "ok");
      this.ollamaModels.set(result.models || []);
      if (result.status !== "ok") {
        this.ollamaStatus.set({text: result.error || "Ollama is not reachable.", kind: "error"});
        return;
      }
      this.validateOllamaSelection();
    } catch (error) {
      this.ollamaAvailable.set(false);
      this.ollamaModels.set([]);
      this.ollamaStatus.set({text: this.errorMessage(error), kind: "error"});
    }
  }

  async loadTranscriptionModels(): Promise<void> {
    try {
      const result = await this.api.transcriptionModels();
      this.whisperModels.set(result.whisper || []);
      this.transcriptionLanguages.set(result.languages || []);
      this.validateWhisperSelection();
    } catch (error) {
      this.whisperModels.set([]);
      this.transcriptionLanguages.set([]);
      this.whisperStatus.set({text: this.errorMessage(error), kind: "error"});
    }
  }

  async downloadSelectedWhisperModel(modelPath = this.processForm.form().localWhisperModel): Promise<void> {
    const model = this.resolveWhisperModel(modelPath) || this.recommendedWhisperModel();
    if (!model) {
      this.whisperStatus.set({text: "Choose a recommended Whisper model before downloading.", kind: "error"});
      return;
    }

    this.whisperStatus.set({text: `Downloading ${model.label} (${model.size})...`, kind: "pending"});
    try {
      const result = await this.api.downloadTranscriptionModel(model.name);
      this.processForm.patch({localWhisperModel: result.path});
      await this.loadTranscriptionModels();
      this.whisperStatus.set({
        text: result.downloaded ? `Ready: downloaded ${model.label}.` : `Ready: ${model.label} was already installed.`,
        kind: "ok",
      });
    } catch (error) {
      this.whisperStatus.set({text: this.errorMessage(error), kind: "error"});
    }
  }

  validateWhisperSelection(): boolean {
    const selection = this.processForm.form().localWhisperModel.trim() || this.config()?.local_whisper_model || "";
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

  recommendedWhisperModel(): WhisperModelOption | null {
    return this.whisperModels().find((model) => model.recommended) || this.whisperModels()[0] || null;
  }

  resolveWhisperModel(pathOrName: string): WhisperModelOption | null {
    const value = pathOrName.trim();
    if (!value) return null;
    return this.whisperModels().find((model) => model.path === value || model.name === value) || null;
  }

  validateOllamaSelection(): boolean {
    const form = this.processForm.form();
    const model = form.ollamaModel.trim() || this.config()?.ollama_model || "qwen2.5:3b";
    if (form.notesBackend !== "ollama") {
      const installed = this.installedModels().join(", ") || "none";
      this.ollamaStatus.set({text: `Installed: ${installed}`, kind: this.ollamaAvailable() ? "muted" : "error"});
      return true;
    }
    if (!this.ollamaAvailable()) {
      this.ollamaStatus.set({text: "Ollama is not reachable.", kind: "error"});
      return false;
    }
    if (!this.isInstalledOllamaModel(model)) {
      this.ollamaStatus.set({text: `Missing: ${model}. Run: ollama pull ${model}`, kind: "error"});
      return false;
    }
    this.ollamaStatus.set({text: `Ready: ${model} is installed locally.`, kind: "ok"});
    return true;
  }

  async startFromForm(options: {skipDuplicateCheck?: boolean; reuseTaskId?: string; forceDownload?: boolean} = {}): Promise<void> {
    const url = this.processForm.form().url.trim();
    if (!url) return;
    await this.startProcessingUrl(url, options);
  }

  async startProcessingUrl(url: string, options: {skipDuplicateCheck?: boolean; reuseTaskId?: string; forceDownload?: boolean} = {}): Promise<void> {
    this.clearPoll();
    if (!options.skipDuplicateCheck && await this.maybeShowDuplicatePanel(url)) {
      return;
    }

    const payload = this.processForm.payload(url, options);
    const selectedModel = payload.ollama_model || this.config()?.ollama_model || "qwen2.5:3b";
    if (payload.transcription_backend === "local" && !this.validateWhisperSelection()) {
      this.setNotice(this.whisperStatus().text, "error");
      this.latestTask.set({
        task_id: "local-check",
        status: "failed",
        error: this.whisperStatus().text,
        logs: [this.localLog("failed", this.whisperStatus().text, "error")],
      });
      return;
    }
    if (payload.notes_backend === "ollama" && !this.isInstalledOllamaModel(selectedModel)) {
      this.setNotice(`Ollama model "${selectedModel}" is not installed.\nRun: ollama pull ${selectedModel}`, "error");
      this.latestTask.set({
        task_id: "local-check",
        status: "failed",
        error: `Missing Ollama model: ${selectedModel}`,
        logs: [this.localLog("failed", `Ollama has ${this.installedModels().join(", ") || "no visible models"}. Missing: ${selectedModel}.`, "error")],
      });
      return;
    }

    this.hideDuplicatePanel();
    this.processForm.patch({url});
    this.latestSummary.set("");
    this.latestTask.set({
      task_id: "queued",
      status: "queued",
      logs: [this.localLog("queued", `Queued ${url}`)],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });
    this.setNotice("Queued", "pending");

    try {
      const task = await this.api.processVideo(payload);
      this.renderTask(task);
      await this.pollTask(task.task_id);
    } catch (error) {
      this.setNotice(this.errorMessage(error), "error");
    }
  }

  useExistingDuplicateOutput(): void {
    const duplicate = this.duplicate();
    const record = duplicate?.record;
    if (!record) return;
    this.hideDuplicatePanel();
    this.renderTask({
      ...record,
      status: "completed",
      completed_at: record.completed_at || record.updated_at,
      logs: [this.localLog("completed", `Using existing output from task ${record.task_id}.`)],
    });
  }

  async regenerateDuplicateSummary(): Promise<void> {
    const record = this.duplicate()?.record;
    const url = this.duplicateUrl();
    if (!record || !url) return;
    this.hideDuplicatePanel();
    await this.startProcessingUrl(url, {skipDuplicateCheck: true, reuseTaskId: record.task_id});
  }

  async forceDuplicateRedownload(): Promise<void> {
    const url = this.duplicateUrl();
    if (!url) return;
    this.hideDuplicatePanel();
    await this.startProcessingUrl(url, {skipDuplicateCheck: true, forceDownload: true});
  }

  async loadRecentTasks(): Promise<void> {
    try {
      this.recentTasks.set((await this.api.tasks()).slice(0, 6));
    } catch (error) {
      this.setNotice(this.errorMessage(error), "error");
    }
  }

  async openRecentTask(taskId: string): Promise<void> {
    const task = await this.api.taskStatus(taskId);
    this.renderTask(task);
    if (!["completed", "failed"].includes(task.status)) {
      await this.pollTask(task.task_id);
    }
  }

  async favoriteLatestSummary(): Promise<void> {
    const taskId = this.latestTask()?.task_id;
    if (!taskId) return;
    try {
      await this.api.favoriteTask(taskId);
      this.setNotice("Summary saved to Favorites.", "ok");
    } catch (error) {
      this.setNotice(this.errorMessage(error), "error");
    }
  }

  async copySummary(): Promise<void> {
    const summary = this.latestSummary();
    if (!summary) return;
    await navigator.clipboard.writeText(summary);
    this.setNotice("Summary copied.", "ok");
  }

  fileHref(kind: "video" | "transcript" | "markdown", task = this.latestTask()): string {
    return task?.task_id ? `/api/history/${encodeURIComponent(task.task_id)}/files/${kind}` : "";
  }

  statusLabel(status = ""): string {
    return statusLabel(status);
  }

  formatElapsed(task: Partial<TaskRecord> | null | undefined): string {
    return formatElapsed(task);
  }

  private async maybeShowDuplicatePanel(url: string): Promise<boolean> {
    try {
      const duplicate = await this.api.lookupHistory(url);
      if (!duplicate.found) {
        this.hideDuplicatePanel();
        return false;
      }
      if (!duplicate.can_reuse) {
        this.hideDuplicatePanel();
        this.setNotice("Found this URL in history, but the saved video file is missing. Downloading again.", "pending");
        return false;
      }
      this.duplicate.set(duplicate);
      this.duplicateUrl.set(url);
      this.setNotice("This video was already downloaded. Choose whether to reuse it or regenerate notes.", "pending");
      return true;
    } catch (error) {
      this.hideDuplicatePanel();
      this.setNotice(`History check failed; continuing normally.\n${this.errorMessage(error)}`, "pending");
      return false;
    }
  }

  private async pollTask(taskId: string): Promise<void> {
    this.clearPoll();
    try {
      const task = await this.api.taskStatus(taskId);
      this.renderTask(task);
      if (!["completed", "failed"].includes(task.status)) {
        this.pollTimer = window.setTimeout(() => void this.pollTask(taskId), 1800);
      }
    } catch (error) {
      this.setNotice(this.errorMessage(error), "error");
    }
  }

  private renderTask(task: TaskRecord): void {
    this.latestTask.set(task);
    if (task.summary) {
      this.latestSummary.set(task.summary);
    } else if (task.task_id) {
      this.latestSummary.set("");
    }

    const elapsed = formatElapsed(task);
    if (task.status === "completed") {
      const cleanupLine = this.videoCleanupLine(task);
      this.setNotice(`Completed in ${elapsed}\nMarkdown: ${task.markdown_path || "-"}${cleanupLine}`, task.video_delete_error ? "error" : "ok");
      void this.loadRecentTasks();
      return;
    }
    if (task.status === "failed") {
      this.setNotice(`Failed after ${elapsed}\n${task.error || "Unknown error"}`, "error");
      void this.loadRecentTasks();
      return;
    }
    this.setNotice(`Working: ${statusLabel(task.status)}\nElapsed: ${elapsed}`, "pending");
  }

  private describePhase(task: TaskRecord | null): string {
    if (!task) return "No active task.";
    if (task.status === "downloading") {
      const parts = [
        task.download_filename || task.url || "video",
        Number.isFinite(Number(task.download_percent)) ? `${Number(task.download_percent).toFixed(1)}%` : "",
        `${formatBytes(task.downloaded_bytes)} / ${formatBytes(task.download_total_bytes)}`,
        formatSpeed(task.download_speed),
        formatEta(task.download_eta) ? `ETA ${formatEta(task.download_eta)}` : "",
      ].filter(Boolean);
      return parts.join(" · ");
    }
    if (task.status === "transcribing") {
      return task.video_path ? `Video saved: ${task.video_path}` : "Preparing transcript.";
    }
    if (task.status === "organizing_notes") {
      const backend = task.summary_backend || task.notes_backend || "extractive";
      const model = task.ollama_model ? ` · ${task.ollama_model}` : "";
      const label = backend === "ollama" ? `Better Local AI Notes${model}` : "Quick Notes";
      return `Writing detailed paragraph summary and segmented notes with ${label}.`;
    }
    if (task.status === "completed") {
      if (task.video_deleted_after_completion) {
        return task.markdown_path
          ? `Markdown ready: ${task.markdown_path}. Local video deleted after completion.`
          : "Task completed. Local video deleted after completion.";
      }
      if (task.video_delete_error) {
        return `Video cleanup failed: ${task.video_delete_error}`;
      }
      return task.markdown_path ? `Markdown ready: ${task.markdown_path}` : "Task completed.";
    }
    if (task.status === "failed") {
      return task.error || "Unknown error.";
    }
    return `Elapsed: ${formatElapsed(task)}`;
  }

  private installedModels(): string[] {
    return this.ollamaModels().map((model) => model.name).filter(Boolean);
  }

  private isInstalledOllamaModel(model: string): boolean {
    return !model || this.installedModels().includes(model);
  }

  private hideDuplicatePanel(): void {
    this.duplicate.set(null);
    this.duplicateUrl.set("");
  }

  private setNotice(text: string, kind: NoticeKind): void {
    this.notice.set({text, kind});
  }

  private videoCleanupLine(task: TaskRecord): string {
    if (task.video_deleted_after_completion) {
      return "\nVideo: deleted after completion";
    }
    if (task.video_delete_error) {
      return `\nVideo cleanup failed: ${task.video_delete_error}`;
    }
    return "";
  }

  private localLog(status: string, message: string, level: TaskLog["level"] = "info"): TaskLog {
    return {
      time: new Date().toISOString().slice(0, 19),
      level,
      status,
      message,
    };
  }

  private clearPoll(): void {
    if (this.pollTimer !== null) {
      window.clearTimeout(this.pollTimer);
      this.pollTimer = null;
    }
  }

  private errorMessage(error: unknown): string {
    return error instanceof Error ? error.message : String(error);
  }
}
