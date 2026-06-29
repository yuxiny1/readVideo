import {DestroyRef, Injectable, computed, inject, signal} from "@angular/core";
import {takeUntilDestroyed} from "@angular/core/rxjs-interop";
import {Observable, forkJoin, map, switchMap, take} from "rxjs";

import {ReadvideoApiService} from "../../../../core/api/readvideo-api/readvideo-api.service";
import {TagSummary, TaskRecord} from "../../../../shared/models/readvideo-types/readvideo.types";
import {errorMessage} from "../../../../shared/utils/errors/errors";
import {formatElapsed} from "../../../../shared/utils/format/format";
import {hasTag, parseTags, tagsFor} from "../../../../shared/utils/tags/tags";

@Injectable()
export class HistoryFacade {
  private readonly api = inject(ReadvideoApiService);
  private readonly destroyRef = inject(DestroyRef);

  readonly records = signal<TaskRecord[]>([]);
  readonly tags = signal<TagSummary[]>([]);
  readonly countLabel = signal("Loading");
  readonly error = signal("");
  readonly notice = signal("");
  readonly searchQuery = signal("");
  readonly activeTag = signal("all");
  readonly tagDrafts: Record<string, string> = {};

  readonly filteredRecords = computed(() => {
    const query = this.searchQuery().trim().toLocaleLowerCase();
    const activeTag = this.activeTag();
    return this.records().filter((record) => {
      const recordTags = tagsFor(record);
      if (activeTag !== "all" && !hasTag(recordTags, activeTag)) return false;
      if (!query) return true;
      return [
        this.title(record),
        record.url,
        record.summary,
        record.markdown_path,
        record.transcription_path,
        record.video_path,
        record.error,
        recordTags.join(" "),
      ].join(" ").toLocaleLowerCase().includes(query);
    });
  });
  readonly visibleCountLabel = computed(() => {
    const count = this.countLabel();
    if (count === "Loading" || count === "Error") return count;
    return `${this.filteredRecords().length} shown / ${this.records().length} records`;
  });

  initialize(): void {
    this.countLabel.set("Loading");
    this.error.set("");
    this.runOnce(
      forkJoin({records: this.api.history(), tags: this.api.tags()}),
      ({records, tags}) => {
        this.applyRecords(records);
        this.tags.set(tags);
      },
    );
  }

  setActiveTag(tag: string): void {
    this.activeTag.set(tag);
  }

  favorite(record: TaskRecord): void {
    this.runOnce(
      this.api.favoriteTask(record.task_id).pipe(switchMap(() => this.api.history())),
      (records) => {
        this.notice.set("Favorite saved");
        this.applyRecords(records);
      },
    );
  }

  saveTags(record: TaskRecord): void {
    const tags = parseTags(this.tagDraft(record));
    this.runOnce(
      this.api.updateHistoryTags(record.task_id, tags).pipe(
        switchMap((updated) => this.api.tags().pipe(map((allTags) => ({updated, allTags})))),
      ),
      ({updated, allTags}) => {
        this.replaceRecord(updated);
        this.tagDrafts[record.task_id] = tagsFor(updated).join(", ");
        this.tags.set(allTags);
        this.notice.set("Tags saved");
      },
    );
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

  tagsFor(record: TaskRecord): string[] {
    return tagsFor(record);
  }

  tagCount(tag: string): number {
    if (tag === "all") return this.records().length;
    return this.records().filter((record) => hasTag(tagsFor(record), tag)).length;
  }

  tagDraft(record: TaskRecord): string {
    this.tagDrafts[record.task_id] ??= tagsFor(record).join(", ");
    return this.tagDrafts[record.task_id];
  }

  setTagDraft(record: TaskRecord, value: string): void {
    this.tagDrafts[record.task_id] = value;
  }

  encodePath(value: string): string {
    return encodeURIComponent(value);
  }

  private applyRecords(records: TaskRecord[]): void {
    this.records.set(records);
    this.syncTagDrafts(records);
    this.countLabel.set(`${records.length} records`);
  }

  private replaceRecord(updated: TaskRecord): void {
    this.records.update((records) => records.map((record) => (
      record.task_id === updated.task_id ? updated : record
    )));
  }

  private syncTagDrafts(records: TaskRecord[]): void {
    const ids = new Set(records.map((record) => record.task_id));
    for (const record of records) this.tagDrafts[record.task_id] ??= tagsFor(record).join(", ");
    for (const id of Object.keys(this.tagDrafts)) {
      if (!ids.has(id)) delete this.tagDrafts[id];
    }
  }

  private runOnce<T>(source$: Observable<T>, next: (value: T) => void): void {
    source$.pipe(
      take(1),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next,
      error: (error) => {
        this.countLabel.set("Error");
        this.error.set(errorMessage(error));
      },
    });
  }
}
