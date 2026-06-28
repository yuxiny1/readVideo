import {DestroyRef, Injectable, computed, inject, signal} from "@angular/core";
import {takeUntilDestroyed} from "@angular/core/rxjs-interop";
import {Router} from "@angular/router";
import {Observable, defer, forkJoin, map, switchMap, take} from "rxjs";

import {ReadvideoApiService} from "../../services/readvideo-api.service";
import {errorMessage} from "../../shared/errors";
import {hasTag, parseTags, tagsFor} from "../../shared/tags";
import {FavoriteFolder, FavoriteSummary, TagSummary} from "../../types/readvideo.types";

@Injectable()
export class FavoritesFacade {
  private readonly api = inject(ReadvideoApiService);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);

  readonly favorites = signal<FavoriteSummary[]>([]);
  readonly folders = signal<FavoriteFolder[]>([]);
  readonly tags = signal<TagSummary[]>([]);
  readonly activeFolderId = signal("all");
  readonly activeTag = signal("all");
  readonly searchQuery = signal("");
  readonly error = signal("");
  readonly notice = signal("");
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
  readonly favoritesCount = computed(() => (
    `${this.filteredFavorites().length} shown / ${this.favorites().length} saved`
  ));

  initialize(): void {
    this.error.set("");
    this.runOnce(
      forkJoin({
        folders: this.api.favoriteFolders(),
        favorites: this.api.favorites(),
        tags: this.api.tags(),
      }),
      ({folders, favorites, tags}) => {
        this.applyFolders(folders);
        this.applyFavorites(favorites);
        this.tags.set(tags);
      },
    );
  }

  setActiveFolder(id: string): void {
    this.activeFolderId.set(id);
  }

  setActiveTag(tag: string): void {
    this.activeTag.set(tag);
  }

  createFolder(): void {
    this.runOnce(
      this.api.addFavoriteFolder(this.folderName.trim(), this.folderNotes.trim()).pipe(
        switchMap(() => this.api.favoriteFolders()),
      ),
      (folders) => {
        this.folderName = "";
        this.folderNotes = "";
        this.notice.set("Folder created");
        this.applyFolders(folders);
      },
    );
  }

  saveFolder(folder: FavoriteFolder): void {
    const draft = this.folderDrafts[folder.id] ?? {name: folder.name, notes: folder.notes};
    this.runOnce(
      this.api.updateFavoriteFolder(folder.id, draft.name.trim(), draft.notes.trim()).pipe(
        switchMap((updated) => this.api.favorites().pipe(map((favorites) => ({updated, favorites})))),
      ),
      ({updated, favorites}) => {
        this.folders.update((folders) => folders.map((item) => item.id === updated.id ? updated : item));
        this.folderDrafts[updated.id] = {name: updated.name, notes: updated.notes};
        this.editingFolderId.set(null);
        this.notice.set("Folder updated");
        this.applyFavorites(favorites);
      },
    );
  }

  assignFolder(item: FavoriteSummary, value: string): void {
    this.runOnce(
      this.api.assignFavoriteFolder(item.id, value ? Number(value) : null).pipe(
        switchMap((updated) => this.api.favoriteFolders().pipe(map((folders) => ({updated, folders})))),
      ),
      ({updated, folders}) => {
        this.replaceFavorite(updated);
        this.applyFolders(folders);
      },
    );
  }

  deleteFavorite(item: FavoriteSummary): void {
    this.runOnce(
      this.api.deleteFavorite(item.id).pipe(
        switchMap(() => forkJoin({
          folders: this.api.favoriteFolders(),
          favorites: this.api.favorites(),
          tags: this.api.tags(),
        })),
      ),
      ({folders, favorites, tags}) => {
        delete this.tagDrafts[item.id];
        this.applyFolders(folders);
        this.applyFavorites(favorites);
        this.tags.set(tags);
      },
    );
  }

  saveTags(item: FavoriteSummary): void {
    this.runOnce(
      this.api.updateFavoriteTags(item.id, parseTags(this.tagDraft(item))).pipe(
        switchMap((updated) => this.api.tags().pipe(map((allTags) => ({updated, allTags})))),
      ),
      ({updated, allTags}) => {
        this.replaceFavorite(updated);
        this.tagDrafts[item.id] = tagsFor(updated).join(", ");
        this.tags.set(allTags);
        this.notice.set("Tags saved");
      },
    );
  }

  readFavorite(item: FavoriteSummary): void {
    if (item.markdown_path) {
      this.openMarkdownPath(item.markdown_path);
      return;
    }
    this.runOnce(
      this.api.favoriteMarkdown(item.id),
      (document) => this.openMarkdownPath(document.path),
    );
  }

  browseFolder(item: FavoriteSummary): void {
    if (item.notes_dir) void this.router.navigate(["/reader"], {queryParams: {folder: item.notes_dir}});
  }

  openFolderInReader(id: string | number): void {
    void this.router.navigate(["/reader"], {queryParams: {favoriteFolderId: String(id)}});
  }

  copyFolderLabel(folder: FavoriteFolder): void {
    this.runOnce(defer(() => navigator.clipboard.writeText(folder.name)), () => {
      this.notice.set("Folder name copied");
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

  favoritesForFolder(id: string | number): FavoriteSummary[] {
    if (id === "all") return this.favorites();
    if (id === "unfiled") return this.favorites().filter((item) => !item.folder_id);
    return this.favorites().filter((item) => item.folder_id === Number(id));
  }

  folderCount(id: string | number): number {
    return this.favoritesForFolder(id).length;
  }

  tagCount(tag: string): number {
    if (tag === "all") return this.favorites().length;
    return this.favorites().filter((item) => hasTag(tagsFor(item), tag)).length;
  }

  folderTags(id: string | number): string[] {
    const values = new Set(this.favoritesForFolder(id).flatMap((item) => tagsFor(item)));
    return [...values].sort((a, b) => a.localeCompare(b, undefined, {sensitivity: "base"})).slice(0, 5);
  }

  folderId(folder: FavoriteFolder): string {
    return String(folder.id);
  }

  folderInitial(folder: FavoriteFolder): string {
    return (folder.name.trim()[0] || "N").toUpperCase();
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

  private replaceFavorite(updated: FavoriteSummary): void {
    this.favorites.update((items) => items.map((item) => item.id === updated.id ? updated : item));
  }

  private applyFavorites(favorites: FavoriteSummary[]): void {
    this.favorites.set(favorites);
    const ids = new Set(favorites.map((item) => item.id));
    for (const item of favorites) this.tagDrafts[item.id] ??= tagsFor(item).join(", ");
    for (const id of Object.keys(this.tagDrafts).map(Number)) {
      if (!ids.has(id)) delete this.tagDrafts[id];
    }
  }

  private applyFolders(folders: FavoriteFolder[]): void {
    this.folders.set(folders);
    const ids = new Set(folders.map((folder) => folder.id));
    for (const folder of folders) {
      this.folderDrafts[folder.id] ??= {name: folder.name, notes: folder.notes};
    }
    for (const id of Object.keys(this.folderDrafts).map(Number)) {
      if (!ids.has(id)) delete this.folderDrafts[id];
    }
  }

  private runOnce<T>(source$: Observable<T>, next: (value: T) => void): void {
    source$.pipe(take(1), takeUntilDestroyed(this.destroyRef)).subscribe({
      next,
      error: (error) => this.error.set(errorMessage(error)),
    });
  }
}
