import {CommonModule} from "@angular/common";
import {Component, computed, inject, OnInit, signal} from "@angular/core";
import {FormsModule} from "@angular/forms";

import {ReadvideoApiService} from "../../services/readvideo-api.service";
import {formatElapsed} from "../../shared/format";
import {TagSummary, TaskRecord} from "../../types/readvideo.types";

@Component({
  selector: "rv-history-page",
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: "./history-page.component.html",
})
export class HistoryPageComponent implements OnInit {
  private readonly api = inject(ReadvideoApiService);

  readonly records = signal<TaskRecord[]>([]);
  readonly tags = signal<TagSummary[]>([]);
  readonly countLabel = signal("Loading");
  readonly error = signal("");
  readonly notice = signal("");
  readonly searchQuery = signal("");
  readonly activeTag = signal("all");
  readonly tagDrafts: Record<string, string> = {};

  readonly filteredRecords = computed(() => {
    const query = this.searchQuery().trim().toLowerCase();
    const activeTag = this.activeTag();
    return this.records().filter((record) => {
      const tags = this.tagsFor(record);
      if (activeTag !== "all" && !this.hasTag(tags, activeTag)) return false;
      if (!query) return true;
      return [
        this.title(record),
        record.url,
        record.summary,
        record.markdown_path,
        record.transcription_path,
        record.video_path,
        record.error,
        tags.join(" "),
      ].join(" ").toLowerCase().includes(query);
    });
  });

  readonly visibleCountLabel = computed(() => {
    if (this.countLabel() === "Loading" || this.countLabel() === "Error") return this.countLabel();
    return `${this.filteredRecords().length} shown / ${this.records().length} records`;
  });

  ngOnInit(): void {
    void this.initialize();
  }

  async initialize(): Promise<void> {
    await Promise.all([this.loadHistory(), this.loadTags()]);
  }

  async loadHistory(): Promise<void> {
    this.countLabel.set("Loading");
    this.error.set("");
    try {
      const records = await this.api.history();
      this.records.set(records);
      this.syncTagDrafts(records);
      this.countLabel.set(`${records.length} records`);
    } catch (error) {
      this.countLabel.set("Error");
      this.error.set(this.message(error));
    }
  }

  async loadTags(): Promise<void> {
    this.tags.set(await this.api.tags());
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
    this.notice.set("Favorite saved");
    await this.loadHistory();
  }

  encodeURIComponent(value: string): string {
    return encodeURIComponent(value);
  }

  tagsFor(record: TaskRecord): string[] {
    return record.tags || [];
  }

  tagCount(tag: string): number {
    if (tag === "all") return this.records().length;
    return this.records().filter((record) => this.hasTag(this.tagsFor(record), tag)).length;
  }

  setActiveTag(tag: string): void {
    this.activeTag.set(tag);
  }

  tagDraft(record: TaskRecord): string {
    if (!(record.task_id in this.tagDrafts)) {
      this.tagDrafts[record.task_id] = this.tagsFor(record).join(", ");
    }
    return this.tagDrafts[record.task_id];
  }

  setTagDraft(record: TaskRecord, value: string): void {
    this.tagDrafts[record.task_id] = value;
  }

  async saveTags(record: TaskRecord): Promise<void> {
    try {
      const updated = await this.api.updateHistoryTags(record.task_id, this.parseTags(this.tagDraft(record)));
      this.replaceRecord(updated);
      this.tagDrafts[record.task_id] = this.tagsFor(updated).join(", ");
      this.notice.set("Tags saved");
      await this.loadTags();
    } catch (error) {
      this.error.set(this.message(error));
    }
  }

  private replaceRecord(updated: TaskRecord): void {
    this.records.update((records) => records.map((record) => record.task_id === updated.task_id ? updated : record));
  }

  private syncTagDrafts(records: TaskRecord[]): void {
    const ids = new Set(records.map((record) => record.task_id));
    for (const record of records) {
      if (!(record.task_id in this.tagDrafts)) {
        this.tagDrafts[record.task_id] = this.tagsFor(record).join(", ");
      }
    }
    for (const id of Object.keys(this.tagDrafts)) {
      if (!ids.has(id)) {
        delete this.tagDrafts[id];
      }
    }
  }

  private parseTags(value: string): string[] {
    return value
      .replace(/(^|\s)#/g, "$1,")
      .split(/[,;\n]+/)
      .map((tag) => tag.trim().replace(/^#/, ""))
      .filter(Boolean);
  }

  private hasTag(tags: string[], tag: string): boolean {
    const needle = tag.toLowerCase();
    return tags.some((item) => item.toLowerCase() === needle);
  }

  private message(error: unknown): string {
    return error instanceof Error ? error.message : String(error);
  }
}
