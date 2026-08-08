import {DestroyRef, Injectable, computed, effect, inject, signal} from "@angular/core";
import {takeUntilDestroyed} from "@angular/core/rxjs-interop";
import {take} from "rxjs";

import {LibraryStore} from "../../../library/data-access/library-store/library.store";
import {FavoriteSummary} from "../../../../shared/models/readvideo-types/readvideo.types";
import {errorMessage} from "../../../../shared/utils/errors/errors";
import {parseTags, tagsFor} from "../../../../shared/utils/tags/tags";
import {ReaderDocumentStore} from "../reader-document/reader-document.store";
import {ReaderHistoryContextService} from "../reader-history-context/reader-history-context.service";

@Injectable()
export class ReaderTagEditorService {
  private readonly library = inject(LibraryStore);
  private readonly document = inject(ReaderDocumentStore);
  private readonly history = inject(ReaderHistoryContextService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly tagDrafts: Record<number, string> = {};

  readonly selectedFavoriteId = signal<number | null>(null);
  readonly error = signal("");
  readonly activeTask = this.history.activeTask;
  readonly activeFavorite = computed(() => (
    this.library.favorites().find((item) => item.id === this.selectedFavoriteId())
      ?? this.library.favorites().find((item) => sameDocumentPath(item.markdown_path, this.document.path()))
      ?? null
  ));
  readonly activeTags = computed(() => tagsFor(this.activeFavorite() ?? this.activeTask() ?? {}));
  readonly canEdit = computed(() => Boolean(this.activeFavorite() || this.activeTask()));

  constructor() {
    effect(() => {
      if (this.library.notice() === "标签已保存") this.document.setStatus("标签已保存");
      if (this.library.error() && this.document.status() === "正在保存标签") {
        this.document.setStatus("标签保存失败");
      }
    });
  }

  selectFavorite(item: FavoriteSummary): void {
    this.error.set("");
    this.selectedFavoriteId.set(item.id);
    this.history.clear();
  }

  selectPath(path: string): FavoriteSummary | null {
    this.error.set("");
    const favorite = this.library.favorites().find((item) => sameDocumentPath(item.markdown_path, path)) ?? null;
    this.selectedFavoriteId.set(favorite?.id ?? null);
    return favorite;
  }

  clearHistory(): void {
    this.history.clear();
  }

  loadHistory(taskId: string): void {
    this.error.set("");
    this.history.load(taskId).pipe(
      take(1),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({error: (error) => {
      this.error.set(errorMessage(error));
      this.document.setStatus("标签加载失败");
    }});
  }

  activeDraft(): string {
    const favorite = this.activeFavorite();
    return favorite ? this.favoriteDraft(favorite) : this.history.activeDraft();
  }

  setActiveDraft(value: string): void {
    const favorite = this.activeFavorite();
    if (favorite) this.tagDrafts[favorite.id] = value;
    else this.history.setActiveDraft(value);
  }

  saveActiveTags(): void {
    const favorite = this.activeFavorite();
    if (!favorite && !this.activeTask()) return;
    this.document.setStatus("正在保存标签");
    this.error.set("");
    if (favorite) {
      this.library.updateTags({favoriteId: favorite.id, tags: parseTags(this.favoriteDraft(favorite))});
      return;
    }
    this.history.saveActiveTags().pipe(
      take(1),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: () => {
        this.library.loadAll();
        this.document.setStatus("标签已保存");
      },
      error: (error) => {
        this.error.set(errorMessage(error));
        this.document.setStatus("标签保存失败");
      },
    });
  }

  favoriteDraft(item: FavoriteSummary): string {
    this.tagDrafts[item.id] ??= tagsFor(item).join(", ");
    return this.tagDrafts[item.id];
  }
}

function sameDocumentPath(left: string, right: string): boolean {
  if (!left || !right) return false;
  if (left === right) return true;
  const leftName = left.split(/[\\/]/).pop();
  const rightName = right.split(/[\\/]/).pop();
  return Boolean(leftName && rightName && leftName === rightName);
}
