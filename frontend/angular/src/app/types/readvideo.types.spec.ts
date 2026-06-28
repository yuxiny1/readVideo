import {describe, expect, it} from "vitest";

import {ProcessPayload, TaskRecord} from "./readvideo.types";

describe("readvideo API type contracts", () => {
  it("represent a local processing request and task response", () => {
    const payload: ProcessPayload = {
      url: "https://example.com/video",
      notes_dir: null,
      transcription_backend: "local",
      transcription_model: null,
      local_whisper_model: "models/ggml-large-v3.bin",
      local_whisper_language: "auto",
      notes_backend: "ollama",
      note_style: "detailed",
      ollama_model: "qwen2.5:32b",
    };
    const task: TaskRecord = {task_id: "task-1", status: "queued", tags: ["course"]};

    expect(payload.notes_backend).toBe("ollama");
    expect(task.tags).toEqual(["course"]);
  });
});
