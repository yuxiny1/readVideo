import {afterEach, beforeEach, describe, expect, it, vi} from "vitest";

import {ProcessFormService} from "./process-form.service";

describe("ProcessFormService", () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => vi.restoreAllMocks());

  it("starts with local-first defaults", () => {
    const service = new ProcessFormService();
    expect(service.form()).toMatchObject({
      transcriptionBackend: "local",
      noteStyle: "detailed",
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
      notesDir: " /notes ",
      transcriptionModel: " whisper-1 ",
      localWhisperModel: " model.bin ",
      localWhisperLanguage: " zh ",
      ollamaModel: " qwen2.5:32b ",
      noteStyle: "commercial",
    });

    expect(service.payload("https://example.com", {reuseTaskId: "old-task", forceDownload: true})).toEqual({
      url: "https://example.com",
      notes_dir: "/notes",
      transcription_backend: "local",
      transcription_model: "whisper-1",
      local_whisper_model: "model.bin",
      local_whisper_language: "zh",
      notes_backend: "ollama",
      note_style: "commercial",
      ollama_model: "qwen2.5:32b",
      reuse_task_id: "old-task",
      force_download: true,
      delete_video_after_completion: false,
    });
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
