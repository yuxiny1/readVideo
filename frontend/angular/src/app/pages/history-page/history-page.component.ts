import {CommonModule} from "@angular/common";
import {Component, inject, OnInit, signal} from "@angular/core";

import {ReadvideoApiService} from "../../services/readvideo-api.service";
import {formatElapsed} from "../../shared/format";
import {TaskRecord} from "../../types/readvideo.types";

@Component({
  selector: "rv-history-page",
  standalone: true,
  imports: [CommonModule],
  templateUrl: "./history-page.component.html",
})
export class HistoryPageComponent implements OnInit {
  private readonly api = inject(ReadvideoApiService);

  readonly records = signal<TaskRecord[]>([]);
  readonly countLabel = signal("Loading");
  readonly error = signal("");

  ngOnInit(): void {
    void this.loadHistory();
  }

  async loadHistory(): Promise<void> {
    this.countLabel.set("Loading");
    this.error.set("");
    try {
      const records = await this.api.history();
      this.records.set(records);
      this.countLabel.set(`${records.length} records`);
    } catch (error) {
      this.countLabel.set("Error");
      this.error.set(this.message(error));
    }
  }

  title(record: TaskRecord): string {
    return record.title || record.url || record.task_id;
  }

  statusClass(record: TaskRecord): string {
    if (record.status === "completed") return "ok";
    if (record.status === "failed") return "error";
    return "pending";
  }

  elapsed(record: TaskRecord): string {
    return formatElapsed(record);
  }

  canFavorite(record: TaskRecord): boolean {
    return Boolean(record.summary || record.markdown_path);
  }

  async favorite(record: TaskRecord): Promise<void> {
    await this.api.favoriteTask(record.task_id);
    await this.loadHistory();
  }

  encodeURIComponent(value: string): string {
    return encodeURIComponent(value);
  }

  private message(error: unknown): string {
    return error instanceof Error ? error.message : String(error);
  }
}
