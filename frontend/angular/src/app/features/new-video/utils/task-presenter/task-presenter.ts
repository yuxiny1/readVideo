import {NoticeKind, TaskLog, TaskRecord} from "../../../../shared/models/readvideo-types/readvideo.types";
import {formatBytes, formatElapsed, formatEta, formatSpeed, statusLabel} from "../../../../shared/utils/format/format";

export const TERMINAL_TASK_STATUSES = new Set(["completed", "failed"]);

export function taskProgressPercent(task: TaskRecord | null): number {
  if (!task) return 0;
  if (task.status === "completed") return 100;
  const percent = Number(task.download_percent);
  return Number.isFinite(percent) ? Math.max(0, Math.min(100, percent)) : 0;
}

export function describeTaskPhase(task: TaskRecord | null): string {
  if (!task) return "No active task.";
  if (task.status === "downloading") return describeDownload(task);
  if (task.status === "transcribing") {
    return task.video_path ? `Video saved: ${task.video_path}` : "Preparing transcript.";
  }
  if (task.status === "organizing_notes") {
    const backend = task.summary_backend || task.notes_backend || "ollama";
    const model = task.ollama_model ? ` · ${task.ollama_model}` : "";
    const label = backend === "ollama" ? `Better Local AI Notes${model}` : "Better Local AI Notes";
    return `Writing detailed paragraph summary and segmented notes with ${label}.`;
  }
  if (task.status === "completed") return describeCompleted(task);
  if (task.status === "failed") return task.error || "Unknown error.";
  return `Elapsed: ${formatElapsed(task)}`;
}

export function taskNotice(task: TaskRecord): {text: string; kind: NoticeKind} {
  const elapsed = formatElapsed(task);
  if (task.status === "completed") {
    const cleanupLine = videoCleanupLine(task);
    return {
      text: `Completed in ${elapsed}\nMarkdown: ${task.markdown_path || "-"}${cleanupLine}`,
      kind: task.video_delete_error ? "error" : "ok",
    };
  }
  if (task.status === "failed") {
    return {text: `Failed after ${elapsed}\n${task.error || "Unknown error"}`, kind: "error"};
  }
  return {text: `Working: ${statusLabel(task.status)}\nElapsed: ${elapsed}`, kind: "pending"};
}

export function localTaskLog(
  status: string,
  message: string,
  level: TaskLog["level"] = "info",
): TaskLog {
  return {
    time: new Date().toISOString().slice(0, 19),
    level,
    status,
    message,
  };
}

function describeDownload(task: TaskRecord): string {
  return [
    task.download_filename || task.url || "video",
    Number.isFinite(Number(task.download_percent)) ? `${Number(task.download_percent).toFixed(1)}%` : "",
    `${formatBytes(task.downloaded_bytes)} / ${formatBytes(task.download_total_bytes)}`,
    formatSpeed(task.download_speed),
    formatEta(task.download_eta) ? `ETA ${formatEta(task.download_eta)}` : "",
  ].filter(Boolean).join(" · ");
}

function describeCompleted(task: TaskRecord): string {
  if (task.video_deleted_after_completion) {
    return task.markdown_path
      ? `Markdown ready: ${task.markdown_path}. Local video deleted after completion.`
      : "Task completed. Local video deleted after completion.";
  }
  if (task.video_delete_error) return `Video cleanup failed: ${task.video_delete_error}`;
  return task.markdown_path ? `Markdown ready: ${task.markdown_path}` : "Task completed.";
}

function videoCleanupLine(task: TaskRecord): string {
  if (task.video_deleted_after_completion) return "\nVideo: deleted after completion";
  if (task.video_delete_error) return `\nVideo cleanup failed: ${task.video_delete_error}`;
  return "";
}
