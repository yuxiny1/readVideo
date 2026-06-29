import {TaskRecord} from "../../models/readvideo-types/readvideo.types";

export const TASK_STATUS_LABELS: Readonly<Record<string, string>> = Object.freeze({
  idle: "空闲",
  queued: "已排队",
  downloading: "正在下载",
  transcribing: "正在转录",
  organizing_notes: "正在整理笔记",
  completed: "已完成",
  failed: "失败",
});

export function statusLabel(status = ""): string {
  return TASK_STATUS_LABELS[String(status || "idle")] ?? "状态未知";
}

export function formatElapsed(task: Partial<TaskRecord> | null | undefined): string {
  const start = Date.parse(task?.created_at || "");
  const end = Date.parse(task?.completed_at || task?.updated_at || new Date().toISOString());
  if (!Number.isFinite(start) || !Number.isFinite(end) || end < start) {
    return "0 秒";
  }

  const seconds = Math.round((end - start) / 1000);
  if (seconds < 60) {
    return `${seconds} 秒`;
  }

  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes} 分 ${remainingSeconds} 秒`;
}

export function formatBytes(value: unknown): string {
  const bytes = Number(value);
  if (!Number.isFinite(bytes) || bytes <= 0) return "-";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let size = bytes;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }
  return unitIndex === 0 ? `${size} ${units[unitIndex]}` : `${size.toFixed(1)} ${units[unitIndex]}`;
}

export function formatSpeed(value: unknown): string {
  const bytes = Number(value);
  if (!Number.isFinite(bytes) || bytes <= 0) return "";
  return `${formatBytes(bytes)}/s`;
}

export function formatEta(value: unknown): string {
  const seconds = Number(value);
  if (!Number.isFinite(seconds) || seconds <= 0) return "";
  if (seconds < 60) return `${Math.round(seconds)} 秒`;
  return `${Math.floor(seconds / 60)} 分 ${Math.round(seconds % 60)} 秒`;
}
