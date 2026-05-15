import {TaskRecord} from "../types/readvideo.types";

export function statusLabel(status = ""): string {
  return String(status || "idle").replaceAll("_", " ");
}

export function formatElapsed(task: Partial<TaskRecord> | null | undefined): string {
  const start = Date.parse(task?.created_at || "");
  const end = Date.parse(task?.completed_at || task?.updated_at || new Date().toISOString());
  if (!Number.isFinite(start) || !Number.isFinite(end) || end < start) {
    return "0s";
  }

  const seconds = Math.round((end - start) / 1000);
  if (seconds < 60) {
    return `${seconds}s`;
  }

  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}m ${remainingSeconds}s`;
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
  if (seconds < 60) return `${Math.round(seconds)}s`;
  return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
}
