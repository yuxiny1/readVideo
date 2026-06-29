import {signal} from "@angular/core";
import {TestBed} from "@angular/core/testing";
import {of, throwError} from "rxjs";
import {afterEach, beforeEach, describe, expect, it, vi} from "vitest";

import {ReadvideoApiService} from "../../../../core/api/readvideo-api/readvideo-api.service";
import {AppConfig, ProcessPayload, TaskRecord} from "../../../../shared/models/readvideo-types/readvideo.types";
import {LocalModelsService} from "../local-models/local-models.service";
import {ProcessFormService} from "../process-form/process-form.service";
import {TaskWorkflowService} from "./task-workflow.service";

const config: AppConfig = {
  transcription_backend: "local",
  download_dir: "/downloads",
  notes_dir: "/notes",
  notes_backend: "ollama",
  note_style: "detailed",
  ollama_model: "qwen:32b",
  local_whisper_model: "models/large.bin",
  local_whisper_language: "auto",
  transcription_model: "",
};

const completedTask: TaskRecord = {
  task_id: "task-1",
  status: "completed",
  markdown_path: "/notes/task.md",
  summary: "Summary",
  created_at: "2026-01-01T00:00:00Z",
  completed_at: "2026-01-01T00:00:05Z",
};

describe("TaskWorkflowService", () => {
  let service: TaskWorkflowService;
  let form: ProcessFormService;
  let api: Record<string, ReturnType<typeof vi.fn>>;
  let models: {
    config: ReturnType<typeof signal<AppConfig | null>>;
    whisperStatus: ReturnType<typeof signal<{text: string; kind: "ok" | "error"}>>;
    initialize: ReturnType<typeof vi.fn>;
    validateWhisperSelection: ReturnType<typeof vi.fn>;
    isInstalledOllamaModel: ReturnType<typeof vi.fn>;
    installedModels: ReturnType<typeof vi.fn>;
  };

  beforeEach(() => {
    localStorage.clear();
    api = {
      health: vi.fn(() => of({status: "ok"})),
      appConfig: vi.fn(() => of(config)),
      tasks: vi.fn(() => of([completedTask])),
      taskStatus: vi.fn(() => of(completedTask)),
      lookupHistory: vi.fn(() => of({found: false, can_reuse: false})),
      processVideo: vi.fn(() => of(completedTask)),
      favoriteTask: vi.fn(() => of({})),
      markdownDocument: vi.fn(() => of({path: "/notes/task.md", content: "# Full note"})),
    };
    models = {
      config: signal<AppConfig | null>(config),
      whisperStatus: signal({text: "Ready", kind: "ok" as const}),
      initialize: vi.fn(),
      validateWhisperSelection: vi.fn(() => true),
      isInstalledOllamaModel: vi.fn(() => true),
      installedModels: vi.fn(() => ["qwen:32b"]),
    };
    TestBed.configureTestingModule({providers: [
      ProcessFormService,
      TaskWorkflowService,
      {provide: ReadvideoApiService, useValue: api},
      {provide: LocalModelsService, useValue: models},
    ]});
    service = TestBed.inject(TaskWorkflowService);
    form = TestBed.inject(ProcessFormService);
    form.patch({localWhisperModel: "models/large.bin", ollamaModel: "qwen:32b"});
  });

  afterEach(() => vi.restoreAllMocks());

  it("initializes health, model configuration, and recent tasks", () => {
    service.initialize();
    expect(service.health()).toBe("Online");
    expect(models.initialize).toHaveBeenCalledWith(config);
    expect(service.recentTasks()).toEqual([completedTask]);
    expect(service.backendLabel()).toContain("Better Local AI Notes");
  });

  it("pauses processing when reusable history is found", () => {
    api.lookupHistory.mockReturnValue(of({found: true, can_reuse: true, record: completedTask}));
    service.startProcessingUrl(" https://example.com/video ");

    expect(api.processVideo).not.toHaveBeenCalled();
    expect(service.duplicateUrl()).toBe("https://example.com/video");
    expect(service.notice().text).toContain("already downloaded");

    service.useExistingDuplicateOutput();
    expect(service.latestTask()?.status).toBe("completed");
    expect(service.duplicate()).toBeNull();
  });

  it("submits a valid local task and renders its result", () => {
    service.startProcessingUrl("https://example.com/video", {skipDuplicateCheck: true});
    expect(api.processVideo).toHaveBeenCalledOnce();
    const payload = api.processVideo.mock.calls[0][0] as ProcessPayload;
    expect(payload.ollama_model).toBe("qwen:32b");
    expect(service.latestTask()).toEqual(completedTask);
    expect(service.latestSummary()).toBe("Summary");
    expect(service.progressPercent()).toBe(100);
  });

  it("blocks processing when the local LLM is missing", () => {
    models.isInstalledOllamaModel.mockReturnValue(false);
    service.startProcessingUrl("https://example.com/video", {skipDuplicateCheck: true});

    expect(api.processVideo).not.toHaveBeenCalled();
    expect(service.latestTask()).toMatchObject({task_id: "local-check", status: "failed"});
    expect(service.notice()).toMatchObject({kind: "error"});
  });

  it("continues when the history lookup fails", () => {
    api.lookupHistory.mockReturnValue(throwError(() => new Error("history offline")));
    service.startProcessingUrl("https://example.com/video");
    expect(api.processVideo).toHaveBeenCalledOnce();
  });

  it("favorites and copies the complete latest output", async () => {
    const writeText = vi.fn(() => Promise.resolve());
    Object.defineProperty(navigator, "clipboard", {configurable: true, value: {writeText}});
    service.latestTask.set(completedTask);
    service.favoriteLatestSummary();
    service.copyLatestOutput();
    await Promise.resolve();
    await Promise.resolve();

    expect(api.favoriteTask).toHaveBeenCalledWith("task-1");
    expect(api.markdownDocument).toHaveBeenCalledWith("/notes/task.md");
    expect(writeText).toHaveBeenCalledWith("# Full note");
  });
});
