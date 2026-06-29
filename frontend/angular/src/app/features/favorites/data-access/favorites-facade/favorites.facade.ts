import {DestroyRef, Injectable, computed, effect, inject, signal} from "@angular/core";
import {takeUntilDestroyed} from "@angular/core/rxjs-interop";
import {Router} from "@angular/router";
import {Observable, defer, take} from "rxjs";

import {ReadvideoApiService} from "../../../../core/api/readvideo-api/readvideo-api.service";
import {LibraryStore} from "../../../library/data-access/library-store/library.store";
import {FavoriteFolder, FavoriteSummary} from "../../../../shared/models/readvideo-types/readvideo.types";
import {errorMessage} from "../../../../shared/utils/errors/errors";
import {hasTag, parseTags, tagsFor} from "../../../../shared/utils/tags/tags";

@Injectable()
export class FavoritesFacade {
  private readonly api = inject(ReadvideoApiService);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  readonly library = inject(LibraryStore);

  readonly favorites = this.library.favorites;
  readonly folders = this.library.folders;
  readonly tags = this.library.tags;
  readonly activeFolderId = signal("all");
  readonly activeTag = signal("all");
  readonly searchQuery = signal("");
  readonly localError = signal("");
  readonly localNotice = signal("");
  readonly error = computed(() => this.localError() || this.library.error());
  readonly notice = computed(() => this.localNotice() || this.library.notice());
  readonly editingFolderId = signal<number | null>(null);
  readonly tagDrafts: Record<number, string> = {};
  readonly folderDrafts: Record<number, {name: string; notes: string}> = {};
  folderName = "";
  folderNotes = "";

  readonly filteredFavorites = computed(() => {
    const folderId = this.activeFolderId();
    const activeTag = this.activeTag();
    const query = this.searchQuery().trim().toLocaleLowerCase();
    return this.favorites().filter((item) => {
      const inFolder = folderId === "all"
        || (folderId === "unfiled" && !item.folder_id)
        || String(item.folder_id) === folderId;
      if (!inFolder) return false;
      const itemTags = tagsFor(item);
      if (activeTag !== "all" && !hasTag(itemTags, activeTag)) return false;
      if (!query) return true;
      return [
        this.title(item),
        item.url,
        item.summary,
        item.markdown_path,
        item.notes_dir,
        item.folder_name,
        itemTags.join(" "),
      ].join(" ").toLocaleLowerCase().includes(query);
    });
  });
  readonly folderCounts = computed(() => {
    const counts: Record<string, number> = {all: this.favorites().length, unfiled: 0};
    for (const item of this.favorites()) {
      const key = item.folder_id ? String(item.folder_id) : "unfiled";
      counts[key] = (counts[key] ?? 0) + 1;
    }
    return counts;
  });
  readonly folderTagLists = computed(() => {
    const values: Record<string, Set<string>> = {all: new Set(), unfiled: new Set()};
    for (const item of this.favorites()) {
      const keys = ["all", item.folder_id ? String(item.folder_id) : "unfiled"];
      for (const key of keys) {
        values[key] ??= new Set();
        for (const tag of tagsFor(item)) values[key].add(tag);
      }
    }
    return Object.fromEntries(Object.entries(values).map(([key, tags]) => [
      key,
      [...tags].sort((a, b) => a.localeCompare(b, undefined, {sensitivity: "base"})).slice(0, 5),
    ])) as Record<string, string[]>;
  });
  readonly tagCounts = computed(() => {
    const counts: Record<string, number> = {all: this.favorites().length};
    for (const item of this.favorites()) {
      for (const tag of tagsFor(item)) {
        const key = tag.toLocaleLowerCase();
        counts[key] = (counts[key] ?? 0) + 1;
      }
    }
    return counts;
  });
  readonly visibleTags = computed(() => this.tags().filter((tag) => this.tagCount(tag.name) > 0));
  readonly favoritesCount = computed(() => (
    `显示 ${this.filteredFavorites().length} 篇，共收藏 ${this.library.favoriteCount()} 篇`
  ));

  constructor() {
    effect(() => {
      const notice = this.library.notice();
      if (notice === "文件夹已创建") {
        this.folderName = "";
        this.folderNotes = "";
      }
      if (notice === "文件夹已更新") this.editingFolderId.set(null);
    });
  }

  initialize(): void {
    this.localError.set("");
    this.localNotice.set("");
    this.library.loadAll();
  }

  setActiveFolder(id: string): void {
    this.activeFolderId.set(id);
  }

  setActiveTag(tag: string): void {
    this.activeTag.set(tag);
  }

  setSearchQuery(query: string): void {
    this.searchQuery.set(query);
  }

  createFolder(): void {
    const name = this.folderName.trim();
    if (!name) return;
    this.beginLibraryAction();
    this.library.createFolder({name, notes: this.folderNotes.trim()});
  }

  saveFolder(folder: FavoriteFolder): void {
    const draft = this.folderDrafts[folder.id] ?? {name: folder.name, notes: folder.notes};
    this.beginLibraryAction();
    this.library.updateFolder({
      folderId: folder.id,
      name: draft.name.trim(),
      notes: draft.notes.trim(),
    });
  }

  assignFolder(item: FavoriteSummary, value: string): void {
    this.beginLibraryAction();
    this.library.assignFolder({
      favoriteId: item.id,
      folderId: value ? Number(value) : null,
    });
  }

  deleteFavorite(item: FavoriteSummary): void {
    this.beginLibraryAction();
    this.library.deleteFavorite(item.id);
  }

  saveTags(item: FavoriteSummary): void {
    this.beginLibraryAction();
    this.library.updateTags({favoriteId: item.id, tags: parseTags(this.tagDraft(item))});
  }

  readFavorite(item: FavoriteSummary): void {
    this.localError.set("");
    if (item.markdown_path) {
      this.openMarkdownPath(item.markdown_path);
      return;
    }
    this.runOnce(this.api.favoriteMarkdown(item.id), (document) => this.openMarkdownPath(document.path));
  }

  browseFolder(item: FavoriteSummary): void {
    if (item.notes_dir) void this.router.navigate(["/reader"], {queryParams: {folder: item.notes_dir}});
  }

  openFolderInReader(id: string | number): void {
    void this.router.navigate(["/reader"], {queryParams: {favoriteFolderId: String(id)}});
  }

  copyFolderLabel(folder: FavoriteFolder): void {
    this.localError.set("");
    this.runOnce(defer(() => navigator.clipboard.writeText(folder.name)), () => {
      this.localNotice.set("文件夹名称已复制");
    });
  }

  beginEditFolder(folder: FavoriteFolder): void {
    this.folderDrafts[folder.id] = {name: folder.name, notes: folder.notes};
    this.editingFolderId.set(folder.id);
  }

  cancelEditFolder(): void {
    this.editingFolderId.set(null);
  }

  folderDraftName(folder: FavoriteFolder): string {
    return this.folderDrafts[folder.id]?.name ?? folder.name;
  }

  folderDraftNotes(folder: FavoriteFolder): string {
    return this.folderDrafts[folder.id]?.notes ?? folder.notes;
  }

  setFolderDraftName(folder: FavoriteFolder, value: string): void {
    const draft = this.folderDrafts[folder.id] ?? {name: folder.name, notes: folder.notes};
    this.folderDrafts[folder.id] = {...draft, name: value};
  }

  setFolderDraftNotes(folder: FavoriteFolder, value: string): void {
    const draft = this.folderDrafts[folder.id] ?? {name: folder.name, notes: folder.notes};
    this.folderDrafts[folder.id] = {...draft, notes: value};
  }

  folderCount(id: string | number): number {
    return this.folderCounts()[String(id)] ?? 0;
  }

  tagCount(tag: string): number {
    return this.tagCounts()[tag.toLocaleLowerCase()] ?? 0;
  }

  folderTags(id: string | number): string[] {
    return this.folderTagLists()[String(id)] ?? [];
  }

  folderId(folder: FavoriteFolder): string {
    return String(folder.id);
  }

  folderInitial(folder: FavoriteFolder): string {
    return (folder.name.trim()[0] || "夹").toUpperCase();
  }

  title(item: FavoriteSummary): string {
    return item.title || item.url || item.task_id;
  }

  tagsFor(item: FavoriteSummary): string[] {
    return tagsFor(item);
  }

  tagDraft(item: FavoriteSummary): string {
    this.tagDrafts[item.id] ??= tagsFor(item).join(", ");
    return this.tagDrafts[item.id];
  }

  setTagDraft(item: FavoriteSummary, value: string): void {
    this.tagDrafts[item.id] = value;
  }

  downloadHref(path: string): string {
    return `/api/markdown_files/download?path=${encodeURIComponent(path)}`;
  }

  private openMarkdownPath(path: string): void {
    void this.router.navigate(["/reader"], {queryParams: {path}});
  }

  private beginLibraryAction(): void {
    this.localError.set("");
    this.localNotice.set("");
  }

  private runOnce<T>(source$: Observable<T>, next: (value: T) => void): void {
    source$.pipe(take(1), takeUntilDestroyed(this.destroyRef)).subscribe({
      next,
      error: (error) => this.localError.set(errorMessage(error)),
    });
  }
}
