import {CommonModule} from "@angular/common";
import {Component, inject} from "@angular/core";

import {TaskWorkflowService} from "../../services/task-workflow.service";
import {TaskRecord} from "../../types/readvideo.types";

@Component({
  selector: "rv-latest-output",
  standalone: true,
  imports: [CommonModule],
  templateUrl: "./latest-output.component.html",
})
export class LatestOutputComponent {
  readonly workflow = inject(TaskWorkflowService);

  canFavorite(task: TaskRecord | null): boolean {
    return Boolean(task?.task_id && (task.summary || task.markdown_path));
  }

  canRead(task: TaskRecord | null): boolean {
    return Boolean(task?.status === "completed" && task.markdown_path);
  }

  readSummary(task: TaskRecord | null): void {
    if (!this.canRead(task) || !task?.markdown_path) return;
    window.location.href = `/reader?path=${encodeURIComponent(task.markdown_path)}`;
  }

  taskPath(task: TaskRecord | null, key: "video_path" | "transcription_path" | "markdown_path"): string {
    return task?.[key] || "-";
  }

  async openTask(taskId: string): Promise<void> {
    await this.workflow.openRecentTask(taskId);
  }
}
