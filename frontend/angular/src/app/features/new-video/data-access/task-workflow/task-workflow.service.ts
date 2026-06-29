import {DestroyRef, Injectable, computed, inject, signal} from "@angular/core";
import {takeUntilDestroyed} from "@angular/core/rxjs-interop";
import {
  EMPTY,
  Observable,
  Subject,
  catchError,
  defer,
  exhaustMap,
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

import {ReadvideoApiService} from "../../../../core/api/readvideo-api/readvideo-api.service";
import {DuplicateLookup, NoticeKind, NoticeState, ProcessPayload, TaskRecord} from "../../../../shared/models/readvideo-types/readvideo.types";
import {errorMessage} from "../../../../shared/utils/errors/errors";
import {statusLabel} from "../../../../shared/utils/format/format";
import {LocalModelsService} from "../local-models/local-models.service";
import {ProcessFormService} from "../process-form/process-form.service";
import {
  TERMINAL_TASK_STATUSES,
  describeTaskPhase,
  localTaskLog,
  taskNotice,
  taskProgressPercent,
} from "../../utils/task-presenter/task-presenter";

export interface StartProcessingOptions {
  skipDuplicateCheck?: boolean;
  reuseTaskId?: string;
  forceDownload?: boolean;
}

interface StartProcessingRequest {
  url: string;
  options: StartProcessingOptions;
}

@Injectable()
export class TaskWorkflowService {
  private readonly api = inject(ReadvideoApiService);
  private readonly processForm = inject(ProcessFormService);
  private readonly models = inject(LocalModelsService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly pollRequests = new Subject<string>();
  private readonly startRequests = new Subject<StartProcessingRequest>();

  readonly config = this.models.config;
  readonly health = signal<"检查中" | "在线" | "离线">("检查中");
  readonly latestTask = signal<TaskRecord | null>(null);
  readonly latestSummary = computed(() => this.latestTask()?.summary ?? "");
  readonly notice = signal<NoticeState>({text: "空闲", kind: "muted"});
  readonly duplicate = signal<DuplicateLookup | null>(null);
  readonly duplicateUrl = signal("");
  readonly recentTasks = signal<TaskRecord[]>([]);

  readonly backendLabel = computed(() => {
    const config = this.config();
    if (!config) return "处理引擎";
    const transcription = config.transcription_backend === "local" ? "本地 Whisper" : "OpenAI 转录";
    return `${transcription}、本地 AI 笔记`;
  });
  readonly taskIdLabel = computed(() => {
    const taskId = this.latestTask()?.task_id;
    return taskId ? `任务 ${taskId}` : "";
  });
  readonly progressPercent = computed(() => taskProgressPercent(this.latestTask()));
  readonly phaseTitle = computed(() => statusLabel(this.latestTask()?.status || "idle"));
  readonly phaseDetail = computed(() => describeTaskPhase(this.latestTask()));
  readonly logs = computed(() => this.latestTask()?.logs ?? []);
  readonly canCopyLatestOutput = computed(() => Boolean(this.latestTask()?.markdown_path || this.latestSummary()));
  readonly canStart = computed(() => {
    const status = this.latestTask()?.status;
    return !status || TERMINAL_TASK_STATUSES.has(status);
  });

  constructor() {
    this.startRequests.pipe(
      exhaustMap(({url, options}) => {
        if (!this.canStart()) {
          this.setNotice("当前任务仍在处理中，请等待完成后再提交新任务。", "pending");
          return EMPTY;
        }
        const ready$ = options.skipDuplicateCheck ? of(true) : this.checkDuplicate(url);
        return ready$.pipe(
          filter(Boolean),
          map(() => this.processForm.payload(url, options)),
          filter((payload) => this.validatePayload(payload)),
          tap(() => this.queueTask(url)),
          switchMap((payload) => this.api.processVideo(payload)),
          catchError((error) => {
            this.setNotice(errorMessage(error), "error");
            return EMPTY;
          }),
        );
      }),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe((task) => {
      this.renderTask(task);
      this.pollRequests.next(task.task_id);
    });

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
        this.health.set(health.status === "ok" ? "在线" : "离线");
        this.models.initialize(config);
        this.loadRecentTasks();
      },
      error: (error) => {
        this.health.set("离线");
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
    this.startRequests.next({url: normalizedUrl, options});
  }

  useExistingDuplicateOutput(): void {
    const record = this.duplicate()?.record;
    if (!record) return;
    this.hideDuplicatePanel();
    this.renderTask({
      ...record,
      status: "completed",
      completed_at: record.completed_at || record.updated_at,
      logs: [localTaskLog("completed", `正在使用任务 ${record.task_id} 的已有输出。`)],
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
      () => this.setNotice("总结已保存到收藏。", "ok"),
    );
  }

  copyLatestOutput(): void {
    const task = this.latestTask();
    const markdownPath = task?.markdown_path;
    const fallbackSummary = this.latestSummary();
    if (!markdownPath && !fallbackSummary) return;

    const content$ = markdownPath
      ? this.api.markdownDocument(markdownPath).pipe(
        map((document) => ({content: document.content, notice: "已复制完整 Markdown 笔记。"})),
      )
      : of({content: fallbackSummary, notice: "已复制总结。"});

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
        this.setNotice(`检查历史记录失败，将继续正常处理。\n${errorMessage(error)}`, "pending");
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
        "历史记录中已有此网址，但本地视频不存在，将重新下载。",
        "pending",
      );
      return true;
    }
    this.duplicate.set(duplicate);
    this.duplicateUrl.set(url);
    this.setNotice(
      "此视频已经下载。请选择复用已有结果、重新生成笔记或重新下载。",
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
      const details = `Ollama 当前可见模型：${this.models.installedModels().join(", ") || "无"}。缺少模型：${selectedModel}。`;
      this.failLocalValidation(`缺少 Ollama 模型：${selectedModel}`, details);
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
    const now = new Date().toISOString();
    this.latestTask.set({
      task_id: "queued",
      status: "queued",
      logs: [localTaskLog("queued", `已将 ${url} 加入队列。`)],
      created_at: now,
      updated_at: now,
    });
    this.setNotice("任务已进入队列", "pending");
  }

  private renderTask(task: TaskRecord): void {
    this.latestTask.set(task);
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
