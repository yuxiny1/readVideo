import {describe, expect, it, vi} from "vitest";

import {ProcessPayload} from "../../../../shared/models/readvideo-types/readvideo.types";
import {ProcessingModelReadiness, processingValidationFailure} from "./processing-readiness";

const payload = (overrides: Partial<ProcessPayload> = {}): ProcessPayload => ({
  url: "https://example.com/video",
  notes_dir: null,
  transcription_backend: "local",
  transcription_model: null,
  local_whisper_model: "models/large.bin",
  mlx_whisper_model: null,
  local_whisper_language: "auto",
  notes_backend: "ollama",
  note_style: "detailed",
  ollama_model: "qwen:32b",
  mlx_model: null,
  ...overrides,
});

const readiness = (overrides: Partial<ProcessingModelReadiness> = {}): ProcessingModelReadiness => ({
  validateWhisperSelection: vi.fn(() => true),
  validateMlxSelection: vi.fn(() => true),
  isInstalledOllamaModel: vi.fn(() => true),
  installedModels: vi.fn(() => ["qwen:32b"]),
  whisperStatus: vi.fn(() => ({text: "Whisper 未就绪", kind: "error" as const})),
  mlxStatus: vi.fn(() => ({text: "MLX 未就绪", kind: "error" as const})),
  ...overrides,
});

describe("processingValidationFailure", () => {
  it("returns the Whisper status when local transcription is unavailable", () => {
    const result = processingValidationFailure(
      payload(),
      null,
      readiness({validateWhisperSelection: vi.fn(() => false)}),
    );
    expect(result?.message).toBe("Whisper 未就绪");
  });

  it("checks MLX readiness only for an MLX request", () => {
    const result = processingValidationFailure(
      payload({notes_backend: "mlx", ollama_model: null, mlx_model: "mlx/model"}),
      null,
      readiness({validateMlxSelection: vi.fn(() => false)}),
    );
    expect(result?.message).toBe("MLX 未就绪");
  });

  it("explains which Ollama model is missing", () => {
    const result = processingValidationFailure(
      payload(),
      null,
      readiness({isInstalledOllamaModel: vi.fn(() => false), installedModels: vi.fn(() => ["qwen:7b"])}),
    );
    expect(result).toEqual({
      message: "缺少 Ollama 模型：qwen:32b",
      logMessage: "Ollama 当前可见模型：qwen:7b。缺少模型：qwen:32b。",
    });
  });
});
