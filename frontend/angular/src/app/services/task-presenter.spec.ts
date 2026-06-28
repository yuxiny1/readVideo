import {afterEach, describe, expect, it, vi} from "vitest";

import {
  TERMINAL_TASK_STATUSES,
  describeTaskPhase,
  localTaskLog,
  taskNotice,
  taskProgressPercent,
} from "./task-presenter";

describe("task presenter", () => {
  afterEach(() => vi.useRealTimers());

  it("clamps task progress and recognizes terminal states", () => {
    expect(taskProgressPercent(null)).toBe(0);
    expect(taskProgressPercent({task_id: "1", status: "downloading", download_percent: 120})).toBe(100);
    expect(taskProgressPercent({task_id: "1", status: "downloading", download_percent: -2})).toBe(0);
    expect(taskProgressPercent({task_id: "1", status: "completed"})).toBe(100);
    expect(TERMINAL_TASK_STATUSES.has("failed")).toBe(true);
  });

  it("describes each important processing phase", () => {
    expect(describeTaskPhase(null)).toBe("No active task.");
    expect(describeTaskPhase({task_id: "1", status: "downloading", download_filename: "video.mp4", download_percent: 50}))
      .toContain("video.mp4 · 50.0%");
    expect(describeTaskPhase({task_id: "1", status: "transcribing", video_path: "/video.mp4"}))
      .toContain("Video saved");
    expect(describeTaskPhase({task_id: "1", status: "organizing_notes", ollama_model: "qwen"}))
      .toContain("qwen");
    expect(describeTaskPhase({task_id: "1", status: "failed", error: "bad audio"})).toBe("bad audio");
  });

  it("describes completion and cleanup outcomes", () => {
    expect(describeTaskPhase({
      task_id: "1", status: "completed", markdown_path: "/note.md", video_deleted_after_completion: true,
    })).toContain("Local video deleted");
    expect(describeTaskPhase({
      task_id: "1", status: "completed", video_delete_error: "permission denied",
    })).toContain("permission denied");
  });

  it("creates notices for active, completed, and failed tasks", () => {
    const dates = {created_at: "2026-01-01T00:00:00Z", completed_at: "2026-01-01T00:00:05Z"};
    expect(taskNotice({task_id: "1", status: "completed", markdown_path: "/note.md", ...dates}))
      .toEqual({text: "Completed in 5s\nMarkdown: /note.md", kind: "ok"});
    expect(taskNotice({task_id: "1", status: "failed", error: "boom", ...dates}).kind).toBe("error");
    expect(taskNotice({task_id: "1", status: "queued", ...dates}).kind).toBe("pending");
  });

  it("creates timestamped local logs", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-02-03T04:05:06Z"));
    expect(localTaskLog("queued", "Ready")).toEqual({
      time: "2026-02-03T04:05:06",
      level: "info",
      status: "queued",
      message: "Ready",
    });
  });
});
