import {afterEach, beforeEach, describe, expect, it, vi} from "vitest";

import {ProcessFormService} from "./process-form.service";

describe("ProcessFormService", () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => vi.restoreAllMocks());

  it("starts with Apple MLX transcription defaults", () => {
    const service = new ProcessFormService();
    expect(service.form()).toMatchObject({
      transcriptionBackend: "mlx",
      noteStyle: "detailed",
      notesBackend: "ollama",
      deleteVideoAfterCompletion: false,
    });
  });

  it("patches state and persists the cleanup preference", () => {
    const service = new ProcessFormService();
    service.patch({url: " video ", deleteVideoAfterCompletion: true});

    expect(service.form().url).toBe(" video ");
    expect(localStorage.getItem("readvideo.deleteVideoAfterCompletion")).toBe("true");
    expect(new ProcessFormService().form().deleteVideoAfterCompletion).toBe(true);
  });

  it("builds a normalized processing payload", () => {
    const service = new ProcessFormService();
    service.patch({
      transcriptionBackend: "local",
      notesDir: " /notes ",
      transcriptionModel: " whisper-1 ",
      localWhisperModel: " model.bin ",
      localWhisperLanguage: " zh ",
      ollamaModel: " qwen3.6:35b ",
      mlxModel: " mlx-community/Qwen2.5-72B-Instruct-3bit ",
      noteStyle: "commercial",
    });

    expect(service.payload("https://example.com", {reuseTaskId: "old-task", forceDownload: true})).toEqual({
      url: "https://example.com",
      notes_dir: "/notes",
      transcription_backend: "local",
      transcription_model: "whisper-1",
      local_whisper_model: "model.bin",
      mlx_whisper_model: null,
      local_whisper_language: "zh",
      notes_backend: "ollama",
      note_style: "commercial",
      ollama_model: "qwen3.6:35b",
      mlx_model: null,
      reuse_task_id: "old-task",
      force_download: true,
      delete_video_after_completion: false,
    });
  });

  it("sends only the model that belongs to the selected notes engine", () => {
    const service = new ProcessFormService();
    service.patch({
      notesBackend: "mlx",
      ollamaModel: "qwen:32b",
      mlxModel: "mlx-community/Qwen2.5-72B-Instruct-3bit",
    });

    const payload = service.payload("https://example.com");
    expect(payload.ollama_model).toBeNull();
    expect(payload.mlx_model).toBe("mlx-community/Qwen2.5-72B-Instruct-3bit");
  });

  it("sends only the model that belongs to the selected transcription engine", () => {
    const service = new ProcessFormService();
    service.patch({
      transcriptionBackend: "mlx",
      localWhisperModel: "models/ggml-large-v3.bin",
      mlxWhisperModel: "mlx-community/whisper-large-v3-mlx",
    });

    const payload = service.payload("https://example.com");
    expect(payload.local_whisper_model).toBeNull();
    expect(payload.mlx_whisper_model).toBe("mlx-community/whisper-large-v3-mlx");
  });

  it("survives unavailable local storage", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });

    const service = new ProcessFormService();
    expect(service.form().deleteVideoAfterCompletion).toBe(false);
    expect(() => service.patch({deleteVideoAfterCompletion: true})).not.toThrow();
  });
});
