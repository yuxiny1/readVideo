import {TestBed} from "@angular/core/testing";
import {of, throwError} from "rxjs";
import {beforeEach, describe, expect, it, vi} from "vitest";

import {ReadvideoApiService} from "../../../../core/api/readvideo-api/readvideo-api.service";
import {AppConfig, OllamaModel, TranscriptionModelsResponse, WhisperModelOption} from "../../../../shared/models/readvideo-types/readvideo.types";
import {LocalModelsService} from "./local-models.service";
import {ProcessFormService} from "../process-form/process-form.service";

const config: AppConfig = {
  transcription_backend: "local",
  download_dir: "/downloads",
  notes_dir: "/notes",
  notes_backend: "ollama",
  note_style: "detailed",
  ollama_model: "small:latest",
  mlx_model: "mlx-community/Qwen2.5-72B-Instruct-3bit",
  mlx_url: "http://127.0.0.1:8080/v1/chat/completions",
  local_whisper_model: "models/small.bin",
  mlx_whisper_model: "mlx-community/whisper-large-v3-mlx",
  mlx_whisper_python: "~/mlx-env/bin/python",
  local_whisper_language: "auto",
  transcription_model: "",
};

const ollamaModel = (name: string, size: number): OllamaModel => ({
  name,
  size,
  size_label: `${size} GB`,
  modified_at: "",
  family: "qwen",
  parameter_size: `${size}B`,
  quantization_level: "Q4",
});

const whisperModel = (overrides: Partial<WhisperModelOption> = {}): WhisperModelOption => ({
  name: "large-v3-turbo",
  label: "Large v3 Turbo",
  size: "1.6 GB",
  path: "models/large-v3-turbo.bin",
  url: "https://example.com/model.bin",
  notes: "Strong local model",
  installed: true,
  recommended: true,
  engine: "whisper_cpp",
  ...overrides,
});

const transcriptionModels = (model = whisperModel()): TranscriptionModelsResponse => ({
  whisper: [model],
  installed_whisper: model.installed ? [model.path] : [],
  mlx_whisper: [],
  installed_mlx_whisper: [],
  mlx_whisper_runtime: {available: true, python: "/mlx/python", error: ""},
  openai: [],
  languages: [{code: "auto", label: "Auto"}],
});

describe("LocalModelsService", () => {
  let service: LocalModelsService;
  let form: ProcessFormService;
  let api: {
    ollamaModels: ReturnType<typeof vi.fn>;
    mlxStatus: ReturnType<typeof vi.fn>;
    transcriptionModels: ReturnType<typeof vi.fn>;
    downloadTranscriptionModel: ReturnType<typeof vi.fn>;
  };

  beforeEach(() => {
    localStorage.clear();
    api = {
      ollamaModels: vi.fn(() => of({
        status: "ok",
        default_model: "small:latest",
        models: [ollamaModel("small:latest", 7), ollamaModel("strong:32b", 32)],
      })),
      mlxStatus: vi.fn(() => of({
        status: "ok",
        default_model: config.mlx_model,
        models: [config.mlx_model],
        start_command: "mlx_lm.server",
      })),
      transcriptionModels: vi.fn(() => of(transcriptionModels())),
      downloadTranscriptionModel: vi.fn(() => of({
        model: "large-v3-turbo",
        path: "models/large-v3-turbo.bin",
        downloaded: true,
      })),
    };
    TestBed.configureTestingModule({providers: [
      ProcessFormService,
      LocalModelsService,
      {provide: ReadvideoApiService, useValue: api},
    ]});
    service = TestBed.inject(LocalModelsService);
    form = TestBed.inject(ProcessFormService);
  });

  it("initializes local defaults and selects the strongest installed models", () => {
    service.initialize(config);

    expect(service.config()).toEqual(config);
    expect(form.form().ollamaModel).toBe("strong:32b");
    expect(form.form().localWhisperModel).toBe("models/large-v3-turbo.bin");
    expect(service.ollamaModelOptions().map((model) => model.name)).toEqual(["strong:32b", "small:latest"]);
    expect(service.ollamaStatus().kind).toBe("ok");
    expect(service.mlxStatus().kind).toBe("ok");
    expect(service.whisperStatus().kind).toBe("ok");
  });

  it("reports missing Ollama and Whisper selections", () => {
    service.ollamaAvailable.set(true);
    service.ollamaModels.set([ollamaModel("installed:7b", 7)]);
    service.whisperCppModels.set([whisperModel({installed: false})]);
    form.patch({
      transcriptionBackend: "local",
      ollamaModel: "missing:32b",
      localWhisperModel: "models/large-v3-turbo.bin",
    });

    expect(service.validateOllamaSelection()).toBe(false);
    expect(service.ollamaStatus().text).toContain("ollama pull missing:32b");
    expect(service.validateWhisperSelection()).toBe(false);
    expect(service.whisperStatus().text).toContain("尚未安装");
  });

  it("downloads the selected Whisper model and refreshes model state", () => {
    service.whisperCppModels.set([whisperModel({installed: false})]);
    form.patch({transcriptionBackend: "local", localWhisperModel: "models/large-v3-turbo.bin"});

    service.downloadSelectedWhisperModel();

    expect(api.downloadTranscriptionModel).toHaveBeenCalledWith("large-v3-turbo");
    expect(api.transcriptionModels).toHaveBeenCalled();
    expect(form.form().localWhisperModel).toBe("models/large-v3-turbo.bin");
    expect(service.whisperStatus()).toMatchObject({kind: "ok"});
  });

  it("surfaces model API failures", () => {
    api.ollamaModels.mockReturnValue(throwError(() => new Error("Ollama offline")));
    api.mlxStatus.mockReturnValue(throwError(() => new Error("MLX offline")));
    api.transcriptionModels.mockReturnValue(throwError(() => new Error("Whisper list failed")));

    service.loadOllamaModels();
    service.loadMlxStatus();
    service.loadTranscriptionModels();

    expect(service.ollamaAvailable()).toBe(false);
    expect(service.ollamaStatus()).toEqual({text: "Ollama offline", kind: "error"});
    expect(service.mlxStatus()).toEqual({text: "MLX offline", kind: "error"});
    expect(service.whisperStatus()).toEqual({text: "Whisper list failed", kind: "error"});
  });

  it("reports the cached MLX model and rejects a different selection", () => {
    service.initialize(config);
    expect(service.validateMlxSelection()).toBe(true);

    form.patch({mlxModel: "mlx-community/another-model"});
    expect(service.validateMlxSelection()).toBe(false);
    expect(service.mlxStatus().text).toContain("本地缓存中没有");
  });

  it("selects the full MLX Whisper model for Apple transcription", () => {
    const mlxWhisper = whisperModel({
      name: "mlx-community/whisper-large-v3-mlx",
      path: "mlx-community/whisper-large-v3-mlx",
      label: "MLX Large v3",
      engine: "mlx",
    });
    api.transcriptionModels.mockReturnValue(of({
      ...transcriptionModels(),
      mlx_whisper: [mlxWhisper],
      installed_mlx_whisper: [mlxWhisper.path],
    }));

    service.initialize({...config, transcription_backend: "mlx"});

    expect(form.form().mlxWhisperModel).toBe(mlxWhisper.path);
    expect(service.whisperModels()).toEqual([mlxWhisper]);
    expect(service.validateWhisperSelection()).toBe(true);
  });
});
