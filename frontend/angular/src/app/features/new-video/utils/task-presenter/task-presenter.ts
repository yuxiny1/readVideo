import {NoticeKind, TaskLog, TaskRecord} from "../../../../shared/models/readvideo-types/readvideo.types";
import {formatBytes, formatElapsed, formatEta, formatSpeed, statusLabel} from "../../../../shared/utils/format/format";

export const TERMINAL_TASK_STATUSES: ReadonlySet<string> = new Set(["completed", "failed"]);

export function taskProgressPercent(task: TaskRecord | null): number {
  if (!task) return 0;
  if (task.status === "completed") return 100;
  const percent = Number(task.download_percent);
  return Number.isFinite(percent) ? Math.max(0, Math.min(100, percent)) : 0;
}

export function describeTaskPhase(task: TaskRecord | null): string {
  if (!task) return "当前没有任务。";
  if (task.status === "downloading") return describeDownload(task);
  if (task.status === "transcribing") {
    return task.video_path ? `视频已保存：${task.video_path}` : "正在准备转录。";
  }
  if (task.status === "organizing_notes") {
    const backend = task.summary_backend || task.notes_backend || "ollama";
    const model = task.ollama_model ? `，模型为 ${task.ollama_model}` : "";
    const label = backend === "ollama" ? `本地 AI 笔记${model}` : "本地提取式笔记";
    return `正在使用${label}生成详细总结和分段笔记。`;
  }
  if (task.status === "completed") return describeCompleted(task);
  if (task.status === "failed") return task.error || "发生未知错误。";
  return `已用时间：${formatElapsed(task)}`;
}

export function taskNotice(task: TaskRecord): {text: string; kind: NoticeKind} {
  const elapsed = formatElapsed(task);
  if (task.status === "completed") {
    const cleanupLine = videoCleanupLine(task);
    return {
      text: `任务已完成，用时 ${elapsed}\nMarkdown 笔记：${task.markdown_path || "-"}${cleanupLine}`,
      kind: task.video_delete_error ? "error" : "ok",
    };
  }
  if (task.status === "failed") {
    return {text: `任务在 ${elapsed} 后失败\n${task.error || "发生未知错误"}`, kind: "error"};
  }
  return {text: `当前状态：${statusLabel(task.status)}\n已用时间：${elapsed}`, kind: "pending"};
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
    formatEta(task.download_eta) ? `预计剩余 ${formatEta(task.download_eta)}` : "",
  ].filter(Boolean).join(" · ");
}

function describeCompleted(task: TaskRecord): string {
  if (task.video_deleted_after_completion) {
    return task.markdown_path
      ? `Markdown 笔记已生成：${task.markdown_path}。任务完成后已删除本地视频。`
      : "任务已完成，并已删除本地视频。";
  }
  if (task.video_delete_error) return `清理视频失败：${task.video_delete_error}`;
  return task.markdown_path ? `Markdown 笔记已生成：${task.markdown_path}` : "任务已完成。";
}

function videoCleanupLine(task: TaskRecord): string {
  if (task.video_deleted_after_completion) return "\n视频：任务完成后已删除";
  if (task.video_delete_error) return `\n清理视频失败：${task.video_delete_error}`;
  return "";
}
