import {DestroyRef, Injectable, computed, inject, signal} from "@angular/core";
import {takeUntilDestroyed} from "@angular/core/rxjs-interop";
import {
  EMPTY,
  Observable,
  Subject,
  catchError,
  defer,
  filter,
  forkJoin,
  map,
  of,
  switchMap,
  take,
  takeWhile,
  tap,
  timer,
} from "rxjs";

import {errorMessage} from "../shared/errors";
import {statusLabel} from "../shared/format";
import {DuplicateLookup, NoticeKind, NoticeState, ProcessPayload, TaskRecord} from "../types/readvideo.types";
import {LocalModelsService} from "./local-models.service";
import {ProcessFormService} from "./process-form.service";
import {ReadvideoApiService} from "./readvideo-api.service";
import {
  TERMINAL_TASK_STATUSES,
  describeTaskPhase,
  localTaskLog,
  taskNotice,
  taskProgressPercent,
} from "./task-presenter";

export interface StartProcessingOptions {
  skipDuplicateCheck?: boolean;
  reuseTaskId?: string;
  forceDownload?: boolean;
}

@Injectable()
export class TaskWorkflowService {
  private readonly api = inject(ReadvideoApiService);
  private readonly processForm = inject(ProcessFormService);
  private readonly models = inject(LocalModelsService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly pollRequests = new Subject<string>();

  readonly config = this.models.config;
  readonly health = signal<"Checking" | "Online" | "Offline">("Checking");
  readonly latestTask = signal<TaskRecord | null>(null);
  readonly latestSummary = signal("");
  readonly notice = signal<NoticeState>({text: "Idle", kind: "muted"});
  readonly duplicate = signal<DuplicateLookup | null>(null);
  readonly duplicateUrl = signal("");
  readonly recentTasks = signal<TaskRecord[]>([]);

  readonly backendLabel = computed(() => {
    const config = this.config();
    return config ? `${config.transcription_backend} / Better Local AI Notes` : "Backend";
  });
  readonly taskIdLabel = computed(() => {
    const taskId = this.latestTask()?.task_id;
    return taskId ? `Task ${taskId}` : "";
  });
  readonly progressPercent = computed(() => taskProgressPercent(this.latestTask()));
  readonly phaseTitle = computed(() => statusLabel(this.latestTask()?.status || "idle"));
  readonly phaseDetail = computed(() => describeTaskPhase(this.latestTask()));
  readonly logs = computed(() => this.latestTask()?.logs ?? []);
  readonly canCopyLatestOutput = computed(() => Boolean(this.latestTask()?.markdown_path || this.latestSummary()));

  constructor() {
    this.pollRequests.pipe(
      switchMap((taskId) => timer(0, 1800).pipe(
        switchMap(() => this.api.taskStatus(taskId)),
        takeWhile((task) => !TERMINAL_TASK_STATUSES.has(task.status), true),
        catchError((error) => {
          this.setNotice(errorMessage(error), "error");
          return EMPTY;
        }),
      )),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe((task) => this.renderTask(task));
  }

  initialize(): void {
    forkJoin({health: this.api.health(), config: this.api.appConfig()}).pipe(
      take(1),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: ({health, config}) => {
        this.health.set(health.status === "ok" ? "Online" : "Offline");
        this.models.initialize(config);
        this.loadRecentTasks();
      },
      error: (error) => {
        this.health.set("Offline");
        this.setNotice(errorMessage(error), "error");
      },
    });
  }

  startFromForm(options: StartProcessingOptions = {}): void {
    const url = this.processForm.form().url.trim();
    if (url) this.startProcessingUrl(url, options);
  }

  startProcessingUrl(url: string, options: StartProcessingOptions = {}): void {
    const normalizedUrl = url.trim();
    if (!normalizedUrl) return;
    const ready$ = options.skipDuplicateCheck
      ? of(true)
      : this.checkDuplicate(normalizedUrl);

    ready$.pipe(
      filter(Boolean),
      map(() => this.processForm.payload(normalizedUrl, options)),
      filter((payload) => this.validatePayload(payload)),
      tap(() => this.queueTask(normalizedUrl)),
      switchMap((payload) => this.api.processVideo(payload)),
      take(1),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: (task) => {
        this.renderTask(task);
        this.pollRequests.next(task.task_id);
      },
      error: (error) => this.setNotice(errorMessage(error), "error"),
    });
  }

  useExistingDuplicateOutput(): void {
    const record = this.duplicate()?.record;
    if (!record) return;
    this.hideDuplicatePanel();
    this.renderTask({
      ...record,
      status: "completed",
      completed_at: record.completed_at || record.updated_at,
      logs: [localTaskLog("completed", `Using existing output from task ${record.task_id}.`)],
    });
  }

  regenerateDuplicateSummary(): void {
    const record = this.duplicate()?.record;
    const url = this.duplicateUrl();
    if (!record || !url) return;
    this.hideDuplicatePanel();
    this.startProcessingUrl(url, {skipDuplicateCheck: true, reuseTaskId: record.task_id});
  }

  forceDuplicateRedownload(): void {
    const url = this.duplicateUrl();
    if (!url) return;
    this.hideDuplicatePanel();
    this.startProcessingUrl(url, {skipDuplicateCheck: true, forceDownload: true});
  }

  loadRecentTasks(): void {
    this.runOnce(
      this.api.tasks().pipe(map((tasks) => tasks.slice(0, 6))),
      (tasks) => this.recentTasks.set(tasks),
    );
  }

  openRecentTask(taskId: string): void {
    this.runOnce(this.api.taskStatus(taskId), (task) => {
      this.renderTask(task);
      if (!TERMINAL_TASK_STATUSES.has(task.status)) this.pollRequests.next(task.task_id);
    });
  }

  favoriteLatestSummary(): void {
    const taskId = this.latestTask()?.task_id;
    if (!taskId) return;
    this.runOnce(
      this.api.favoriteTask(taskId),
      () => this.setNotice("Summary saved to Favorites.", "ok"),
    );
  }

  copyLatestOutput(): void {
    const task = this.latestTask();
    const markdownPath = task?.markdown_path;
    const fallbackSummary = this.latestSummary();
    if (!markdownPath && !fallbackSummary) return;

    const content$ = markdownPath
      ? this.api.markdownDocument(markdownPath).pipe(
        map((document) => ({content: document.content, notice: "Full Markdown note copied."})),
      )
      : of({content: fallbackSummary, notice: "Summary copied."});

    this.runOnce(
      content$.pipe(
        switchMap(({content, notice}) => defer(() => navigator.clipboard.writeText(content)).pipe(
          map(() => notice),
        )),
      ),
      (notice) => this.setNotice(notice, "ok"),
    );
  }

  private checkDuplicate(url: string): Observable<boolean> {
    return this.api.lookupHistory(url).pipe(
      map((duplicate) => this.applyDuplicateLookup(url, duplicate)),
      catchError((error) => {
        this.hideDuplicatePanel();
        this.setNotice(`History check failed; continuing normally.\n${errorMessage(error)}`, "pending");
        return of(true);
      }),
    );
  }

  private applyDuplicateLookup(url: string, duplicate: DuplicateLookup): boolean {
    if (!duplicate.found) {
      this.hideDuplicatePanel();
      return true;
    }
    if (!duplicate.can_reuse) {
      this.hideDuplicatePanel();
      this.setNotice(
        "Found this URL in history, but the saved video file is missing. Downloading again.",
        "pending",
      );
      return true;
    }
    this.duplicate.set(duplicate);
    this.duplicateUrl.set(url);
    this.setNotice(
      "This video was already downloaded. Choose whether to reuse it or regenerate notes.",
      "pending",
    );
    return false;
  }

  private validatePayload(payload: ProcessPayload): boolean {
    if (payload.transcription_backend === "local" && !this.models.validateWhisperSelection()) {
      this.failLocalValidation(this.models.whisperStatus().text);
      return false;
    }
    const selectedModel = payload.ollama_model || this.config()?.ollama_model || "qwen2.5:32b";
    if (!this.models.isInstalledOllamaModel(selectedModel)) {
      const details = `Ollama has ${this.models.installedModels().join(", ") || "no visible models"}. Missing: ${selectedModel}.`;
      this.failLocalValidation(`Missing Ollama model: ${selectedModel}`, details);
      return false;
    }
    return true;
  }

  private failLocalValidation(message: string, logMessage = message): void {
    this.setNotice(message, "error");
    this.latestTask.set({
      task_id: "local-check",
      status: "failed",
      error: message,
      logs: [localTaskLog("failed", logMessage, "error")],
    });
  }

  private queueTask(url: string): void {
    this.hideDuplicatePanel();
    this.processForm.patch({url});
    this.latestSummary.set("");
    const now = new Date().toISOString();
    this.latestTask.set({
      task_id: "queued",
      status: "queued",
      logs: [localTaskLog("queued", `Queued ${url}`)],
      created_at: now,
      updated_at: now,
    });
    this.setNotice("Queued", "pending");
  }

  private renderTask(task: TaskRecord): void {
    this.latestTask.set(task);
    this.latestSummary.set(task.summary ?? "");
    this.notice.set(taskNotice(task));
    if (TERMINAL_TASK_STATUSES.has(task.status)) this.loadRecentTasks();
  }

  private hideDuplicatePanel(): void {
    this.duplicate.set(null);
    this.duplicateUrl.set("");
  }

  private setNotice(text: string, kind: NoticeKind): void {
    this.notice.set({text, kind});
  }

  private runOnce<T>(source$: Observable<T>, next: (value: T) => void): void {
    source$.pipe(
      take(1),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next,
      error: (error) => this.setNotice(errorMessage(error), "error"),
    });
  }
}
