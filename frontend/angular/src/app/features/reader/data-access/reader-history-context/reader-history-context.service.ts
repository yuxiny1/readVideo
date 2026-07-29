import {Injectable, inject, signal} from "@angular/core";
import {Observable, tap, throwError} from "rxjs";

import {ReadvideoApiService} from "../../../../core/api/readvideo-api/readvideo-api.service";
import {TaskRecord} from "../../../../shared/models/readvideo-types/readvideo.types";
import {parseTags, tagsFor} from "../../../../shared/utils/tags/tags";

@Injectable()
export class ReaderHistoryContextService {
  private readonly api = inject(ReadvideoApiService);
  readonly activeTask = signal<TaskRecord | null>(null);
  private readonly tagDrafts: Record<string, string> = {};

  clear(): void {
    this.activeTask.set(null);
  }

  load(taskId: string): Observable<TaskRecord> {
    return this.api.taskStatus(taskId).pipe(tap((task) => this.applyTask(task)));
  }

  activeDraft(): string {
    const task = this.activeTask();
    return task ? this.tagDraft(task) : "";
  }

  setActiveDraft(value: string): void {
    const task = this.activeTask();
    if (task) this.tagDrafts[task.task_id] = value;
  }

  saveActiveTags(): Observable<TaskRecord> {
    const task = this.activeTask();
    if (!task) return throwError(() => new Error("当前阅读笔记没有可保存标签的历史任务。"));
    const tags = parseTags(this.tagDraft(task));
    return this.api.updateHistoryTags(task.task_id, tags).pipe(tap((updated) => this.applyTask(updated)));
  }

  private tagDraft(task: TaskRecord): string {
    this.tagDrafts[task.task_id] ??= tagsFor(task).join(", ");
    return this.tagDrafts[task.task_id];
  }

  private applyTask(task: TaskRecord): void {
    this.activeTask.set(task);
    this.tagDrafts[task.task_id] = tagsFor(task).join(", ");
  }
}
