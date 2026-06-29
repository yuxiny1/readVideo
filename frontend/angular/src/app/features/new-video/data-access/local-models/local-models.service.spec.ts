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
  local_whisper_model: "models/small.bin",
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
  ...overrides,
});

const transcriptionModels = (model = whisperModel()): TranscriptionModelsResponse => ({
  whisper: [model],
  installed_whisper: model.installed ? [model.path] : [],
  openai: [],
  languages: [{code: "auto", label: "Auto"}],
});

describe("LocalModelsService", () => {
  let service: LocalModelsService;
  let form: ProcessFormService;
  let api: {
    ollamaModels: ReturnType<typeof vi.fn>;
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
    expect(service.whisperStatus().kind).toBe("ok");
  });

  it("reports missing Ollama and Whisper selections", () => {
    service.ollamaAvailable.set(true);
    service.ollamaModels.set([ollamaModel("installed:7b", 7)]);
    service.whisperModels.set([whisperModel({installed: false})]);
    form.patch({ollamaModel: "missing:32b", localWhisperModel: "models/large-v3-turbo.bin"});

    expect(service.validateOllamaSelection()).toBe(false);
    expect(service.ollamaStatus().text).toContain("ollama pull missing:32b");
    expect(service.validateWhisperSelection()).toBe(false);
    expect(service.whisperStatus().text).toContain("尚未安装");
  });

  it("downloads the selected Whisper model and refreshes model state", () => {
    service.whisperModels.set([whisperModel({installed: false})]);
    form.patch({localWhisperModel: "models/large-v3-turbo.bin"});

    service.downloadSelectedWhisperModel();

    expect(api.downloadTranscriptionModel).toHaveBeenCalledWith("large-v3-turbo");
    expect(api.transcriptionModels).toHaveBeenCalled();
    expect(form.form().localWhisperModel).toBe("models/large-v3-turbo.bin");
    expect(service.whisperStatus()).toMatchObject({kind: "ok"});
  });

  it("surfaces model API failures", () => {
    api.ollamaModels.mockReturnValue(throwError(() => new Error("Ollama offline")));
    api.transcriptionModels.mockReturnValue(throwError(() => new Error("Whisper list failed")));

    service.loadOllamaModels();
    service.loadTranscriptionModels();

    expect(service.ollamaAvailable()).toBe(false);
    expect(service.ollamaStatus()).toEqual({text: "Ollama offline", kind: "error"});
    expect(service.whisperStatus()).toEqual({text: "Whisper list failed", kind: "error"});
  });
});
