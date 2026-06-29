import {CommonModule} from "@angular/common";
import {ChangeDetectionStrategy, Component, input, output} from "@angular/core";

import {TaskRecord} from "../../../../shared/models/readvideo-types/readvideo.types";
import {formatElapsed, statusLabel} from "../../../../shared/utils/format/format";

export interface LatestOutputViewModel {
  task: TaskRecord | null;
  summary: string;
  recentTasks: TaskRecord[];
  canCopy: boolean;
}

@Component({
  selector: "rv-latest-output",
  standalone: true,
  imports: [CommonModule],
  templateUrl: "./latest-output.component.html",
  styleUrl: "./latest-output.component.scss",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LatestOutputComponent {
  readonly vm = input.required<LatestOutputViewModel>();
  readonly favoriteRequested = output<void>();
  readonly copyRequested = output<void>();
  readonly refreshRequested = output<void>();
  readonly taskOpened = output<string>();
  readonly readerOpened = output<string>();

  canFavorite(task: TaskRecord | null): boolean {
    return Boolean(task?.task_id && (task.summary || task.markdown_path));
  }

  canRead(task: TaskRecord | null): boolean {
    return Boolean(task?.status === "completed" && task.markdown_path);
  }

  readSummary(task: TaskRecord | null): void {
    if (this.canRead(task) && task?.markdown_path) this.readerOpened.emit(task.markdown_path);
  }

  taskPath(task: TaskRecord | null, key: "video_path" | "transcription_path" | "markdown_path"): string {
    return task?.[key] || "-";
  }

  fileHref(kind: "video" | "transcript" | "markdown", task: TaskRecord | null): string {
    return task?.task_id ? `/api/history/${encodeURIComponent(task.task_id)}/files/${kind}` : "";
  }

  statusLabel(status: string): string {
    return statusLabel(status);
  }

  formatElapsed(task: Partial<TaskRecord> | null | undefined): string {
    return formatElapsed(task);
  }
}
