import {DestroyRef, Injectable, inject, signal} from "@angular/core";
import {takeUntilDestroyed} from "@angular/core/rxjs-interop";
import {Observable, switchMap, take} from "rxjs";

import {ReadvideoApiService} from "../../services/readvideo-api.service";
import {TaskWorkflowService} from "../../services/task-workflow.service";
import {errorMessage} from "../../shared/errors";
import {SourceUpdate, WatchItem} from "../../types/readvideo.types";

@Injectable()
export class SavedSourcesFacade {
  private readonly api = inject(ReadvideoApiService);
  private readonly workflow = inject(TaskWorkflowService);
  private readonly destroyRef = inject(DestroyRef);

  readonly items = signal<WatchItem[]>([]);
  readonly updates = signal<Record<string, SourceUpdate[]>>({});
  readonly errors = signal<Record<string, string>>({});
  readonly orderSaving = signal(false);
  newItem = {name: "", url: "", notes: ""};

  loadWatchlist(): void {
    this.runOnce(this.api.watchlist(), (items) => {
      this.items.set(items);
      this.setError("list", "");
    }, "list");
  }

  addWatchItem(): void {
    const item = {
      name: this.newItem.name.trim(),
      url: this.newItem.url.trim(),
      notes: this.newItem.notes.trim(),
    };
    this.runOnce(
      this.api.addWatchItem(item).pipe(switchMap(() => this.api.watchlist())),
      (items) => {
        this.newItem = {name: "", url: "", notes: ""};
        this.items.set(items);
      },
    );
  }

  loadUpdates(item: WatchItem): void {
    const key = String(item.id);
    this.setError(key, "");
    this.updates.update((updates) => ({...updates, [key]: []}));
    this.runOnce(
      this.api.sourceUpdates(item.id),
      (result) => this.updates.update((updates) => ({...updates, [key]: result.updates})),
      key,
    );
  }

  deleteItem(item: WatchItem): void {
    this.runOnce(
      this.api.deleteWatchItem(item.id).pipe(switchMap(() => this.api.watchlist())),
      (items) => this.items.set(items),
    );
  }

  persistOrder(items: WatchItem[], fallback: WatchItem[]): void {
    this.items.set(items);
    this.orderSaving.set(true);
    this.api.reorderWatchItems(items.map((item) => item.id)).pipe(
      take(1),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: (savedItems) => {
        this.items.set(savedItems);
        this.orderSaving.set(false);
      },
      error: (error) => {
        this.items.set(fallback);
        this.orderSaving.set(false);
        this.workflow.notice.set({text: errorMessage(error), kind: "error"});
      },
    });
  }

  private setError(key: string, value: string): void {
    this.errors.update((errors) => ({...errors, [key]: value}));
  }

  private runOnce<T>(source$: Observable<T>, next: (value: T) => void, errorKey = ""): void {
    source$.pipe(take(1), takeUntilDestroyed(this.destroyRef)).subscribe({
      next,
      error: (error) => {
        const message = errorMessage(error);
        if (errorKey) this.setError(errorKey, message);
        else this.workflow.notice.set({text: message, kind: "error"});
      },
    });
  }
}
