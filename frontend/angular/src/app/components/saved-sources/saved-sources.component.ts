import {CommonModule} from "@angular/common";
import {Component, inject, OnInit, signal} from "@angular/core";
import {FormsModule} from "@angular/forms";

import {ProcessFormService} from "../../services/process-form.service";
import {ReadvideoApiService} from "../../services/readvideo-api.service";
import {TaskWorkflowService} from "../../services/task-workflow.service";
import {SourceUpdate, WatchItem} from "../../types/readvideo.types";

@Component({
  selector: "rv-saved-sources",
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: "./saved-sources.component.html",
})
export class SavedSourcesComponent implements OnInit {
  private readonly api = inject(ReadvideoApiService);
  private readonly form = inject(ProcessFormService);
  readonly workflow = inject(TaskWorkflowService);

  readonly items = signal<WatchItem[]>([]);
  readonly updates = signal<Record<string, SourceUpdate[]>>({});
  readonly errors = signal<Record<string, string>>({});
  newItem = {name: "", url: "", notes: ""};

  ngOnInit(): void {
    void this.loadWatchlist();
  }

  async loadWatchlist(): Promise<void> {
    try {
      this.items.set(await this.api.watchlist());
      this.errors.update((errors) => ({...errors, list: ""}));
    } catch (error) {
      this.errors.update((errors) => ({...errors, list: this.message(error)}));
    }
  }

  async addWatchItem(): Promise<void> {
    try {
      await this.api.addWatchItem({
        name: this.newItem.name.trim(),
        url: this.newItem.url.trim(),
        notes: this.newItem.notes.trim(),
      });
      this.newItem = {name: "", url: "", notes: ""};
      await this.loadWatchlist();
    } catch (error) {
      this.workflow.notice.set({text: this.message(error), kind: "error"});
    }
  }

  useUrl(url: string): void {
    this.form.patch({url});
  }

  async downloadUrl(url: string): Promise<void> {
    this.form.patch({url});
    await this.workflow.startProcessingUrl(url);
  }

  async loadUpdates(item: WatchItem): Promise<void> {
    this.errors.update((errors) => ({...errors, [item.id]: ""}));
    this.updates.update((updates) => ({...updates, [item.id]: []}));
    try {
      const result = await this.api.sourceUpdates(item.id);
      this.updates.update((updates) => ({...updates, [item.id]: result.updates}));
    } catch (error) {
      this.errors.update((errors) => ({...errors, [item.id]: this.message(error)}));
    }
  }

  async deleteItem(item: WatchItem): Promise<void> {
    await this.api.deleteWatchItem(item.id);
    await this.loadWatchlist();
  }

  updateMeta(update: SourceUpdate): string {
    return [update.uploader, update.upload_date].filter(Boolean).join(" / ");
  }

  private message(error: unknown): string {
    return error instanceof Error ? error.message : String(error);
  }
}
