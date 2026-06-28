import {DestroyRef, Injectable, computed, inject, signal} from "@angular/core";
import {takeUntilDestroyed} from "@angular/core/rxjs-interop";
import {ActivatedRoute, Router} from "@angular/router";
import {Observable, catchError, forkJoin, map, of, switchMap, take} from "rxjs";

import {ReadvideoApiService} from "../../services/readvideo-api.service";
import {errorMessage} from "../../shared/errors";
import {parseTags, tagsFor} from "../../shared/tags";
import {
  FavoriteFolder,
  FavoriteSummary,
  MarkdownDocument,
  MarkdownFile,
  TagSummary,
} from "../../types/readvideo.types";
import {favoriteTitle, filterFavorites, filterFiles, libraryItems} from "./reader-library";
import {ReaderDocumentStore} from "./reader-document.store";
import {LibraryMode, LibrarySort, ReaderLibraryItem} from "./reader.types";

@Injectable()
export class ReaderFacade {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(ReadvideoApiService);
  private readonly destroyRef = inject(DestroyRef);
  readonly document = inject(ReaderDocumentStore);

  readonly favorites = signal<FavoriteSummary[]>([]);
  readonly folders = signal<FavoriteFolder[]>([]);
  readonly tags = signal<TagSummary[]>([]);
  readonly activeFolderId = signal("all");
  readonly activeTag = signal("all");
  readonly files = signal<MarkdownFile[]>([]);
  readonly fileCount = signal("0 files");
  readonly defaultNotesDir = signal("notes");
  readonly libraryError = signal("");
  readonly error = computed(() => this.document.error() || this.libraryError());
  readonly searchQuery = signal("");
  readonly libraryMode = signal<LibraryMode>("all");
  readonly librarySort = signal<LibrarySort>("recent");
  readonly tagDrafts: Record<number, string> = {};
  markdownFolder = "notes";

  readonly filteredFavorites = computed(() => filterFavorites(
    this.favorites(),
    this.activeFolderId(),
    this.activeTag(),
    this.searchQuery(),
    this.librarySort(),
  ));
  readonly visibleFavoriteNotes = computed(() => this.filteredFavorites().slice(0, 3));
  readonly filteredFiles = computed(() => filterFiles(
    this.files(),
    this.searchQuery(),
    this.librarySort(),
  ));
  readonly visibleLibraryItems = computed(() => libraryItems(
    this.libraryMode(),
    this.filteredFavorites(),
    this.filteredFiles(),
  ));
  readonly libraryCount = computed(() => `${this.filteredFavorites().length} favorites · ${this.fileCount()}`);
  readonly activeFavorite = computed(() => (
    this.favorites().find((item) => item.markdown_path === this.document.path()) ?? null
  ));
  readonly activeDocumentTags = computed(() => tagsFor(this.activeFavorite() ?? {}));
  readonly activeLibraryIndex = computed(() => {
    const currentPath = this.document.path();
    return currentPath
      ? this.availableLibraryItems().findIndex((item) => item.path === currentPath)
      : -1;
  });
  readonly canOpenPrevious = computed(() => this.activeLibraryIndex() > 0);
  readonly canOpenNext = computed(() => {
    const index = this.activeLibraryIndex();
    return index >= 0 && index < this.availableLibraryItems().length - 1;
  });
  readonly folderCounts = computed(() => {
    const counts: Record<string, number> = {all: this.favorites().length, unfiled: 0};
    for (const item of this.favorites()) {
      if (!item.folder_id) counts["unfiled"] += 1;
      else counts[String(item.folder_id)] = (counts[String(item.folder_id)] ?? 0) + 1;
    }
    return counts;
  });
  readonly tagCounts = computed(() => {
    const counts: Record<string, number> = {all: this.favorites().length};
    for (const item of this.favorites()) {
      for (const tag of tagsFor(item)) counts[tag.toLocaleLowerCase()] = (counts[tag.toLocaleLowerCase()] ?? 0) + 1;
    }
    return counts;
  });

  initialize(): void {
    this.libraryError.set("");
    this.runOnce(
      forkJoin({
        config: this.recover(this.api.appConfig(), null),
        favorites: this.recover(this.api.favorites(), []),
        folders: this.recover(this.api.favoriteFolders(), []),
        tags: this.recover(this.api.tags(), []),
      }),
      ({config, favorites, folders, tags}) => {
        this.defaultNotesDir.set(config?.notes_dir || "notes");
        this.markdownFolder = this.defaultNotesDir();
        this.applyFavorites(favorites);
        this.folders.set(folders);
        this.tags.set(tags);
        this.applyInitialRoute();
      },
    );
  }

  loadMarkdownFiles(
    directory = this.markdownFolder.trim() || this.defaultNotesDir(),
    updateRoute = false,
  ): void {
    this.fileCount.set("Loading");
    this.runOnce(this.api.markdownFiles(directory), (files) => {
      this.markdownFolder = directory;
      this.files.set(files);
      this.fileCount.set(`${files.length} files`);
      if (updateRoute) {
        void this.router.navigate([], {
          relativeTo: this.route,
          queryParams: {folder: directory, path: null},
          queryParamsHandling: "merge",
        });
      }
    }, () => {
      this.files.set([]);
      this.fileCount.set("Error");
    });
  }

  openFavorite(item: FavoriteSummary): void {
    if (item.notes_dir && item.notes_dir !== this.markdownFolder) this.loadMarkdownFiles(item.notes_dir);
    if (item.markdown_path) {
      this.openPath(item.markdown_path);
      return;
    }
    this.runOnce(this.api.favoriteMarkdown(item.id), (document) => this.applyDocument(document, true));
  }

  openFile(file: MarkdownFile): void {
    this.openPath(file.path);
  }

  openPath(path: string, updateRoute = true): void {
    this.document.beginOpen(path);
    this.libraryError.set("");
    this.runOnce(
      this.api.markdownDocument(path),
      (document) => this.applyDocument(document, updateRoute),
      (message) => this.document.fail(message),
    );
  }

  openAdjacent(direction: -1 | 1): void {
    const next = this.availableLibraryItems()[this.activeLibraryIndex() + direction];
    if (next) this.openLibraryItem(next);
  }

  openLibraryItem(item: ReaderLibraryItem): void {
    if (item.favorite) this.openFavorite(item.favorite);
    else if (item.file) this.openFile(item.file);
  }

  setLibraryMode(mode: LibraryMode): void {
    this.libraryMode.set(mode);
  }

  setActiveTag(tag: string): void {
    this.activeTag.set(tag);
  }

  setActiveFavoriteFolder(id: string): void {
    const valid = id === "all" || id === "unfiled" || this.folders().some((folder) => String(folder.id) === id);
    this.activeFolderId.set(valid ? id : "all");
  }

  setLibrarySort(sort: string): void {
    if (["recent", "title", "folder", "path"].includes(sort)) this.librarySort.set(sort as LibrarySort);
  }

  activeTagDraft(): string {
    const item = this.activeFavorite();
    return item ? this.tagDraft(item) : "";
  }

  setActiveTagDraft(value: string): void {
    const item = this.activeFavorite();
    if (item) this.tagDrafts[item.id] = value;
  }

  saveActiveTags(): void {
    const item = this.activeFavorite();
    if (!item) return;
    this.runOnce(
      this.api.updateFavoriteTags(item.id, parseTags(this.tagDraft(item))).pipe(
        switchMap((updated) => this.api.tags().pipe(map((allTags) => ({updated, allTags})))),
      ),
      ({updated, allTags}) => {
        this.replaceFavorite(updated);
        this.tagDrafts[item.id] = tagsFor(updated).join(", ");
        this.tags.set(allTags);
        this.document.status.set("Tags saved");
      },
    );
  }

  folderCount(id: string | number): number {
    return this.folderCounts()[String(id)] ?? 0;
  }

  tagCount(tag: string): number {
    return this.tagCounts()[tag.toLocaleLowerCase()] ?? 0;
  }

  folderId(folder: FavoriteFolder): string {
    return String(folder.id);
  }

  titleFor(item: FavoriteSummary): string {
    return favoriteTitle(item);
  }

  tagsFor(item: FavoriteSummary): string[] {
    return tagsFor(item);
  }

  tagDraft(item: FavoriteSummary): string {
    this.tagDrafts[item.id] ??= tagsFor(item).join(", ");
    return this.tagDrafts[item.id];
  }

  isActivePath(path: string): boolean {
    return this.document.path() === path;
  }

  private applyInitialRoute(): void {
    const folderId = this.route.snapshot.queryParamMap.get("favoriteFolderId");
    if (folderId) {
      this.setActiveFavoriteFolder(folderId);
      this.libraryMode.set("favorites");
    }
    const folder = this.route.snapshot.queryParamMap.get("folder") || this.markdownFolder;
    this.loadMarkdownFiles(folder);
    const path = this.route.snapshot.queryParamMap.get("path");
    if (path) this.openPath(path, false);
  }

  private applyDocument(document: MarkdownDocument, updateRoute: boolean): void {
    this.document.open(document);
    if (updateRoute) {
      void this.router.navigate([], {
        relativeTo: this.route,
        queryParams: {path: document.path, folder: this.markdownFolder},
        queryParamsHandling: "merge",
      });
    }
  }

  private availableLibraryItems(): ReaderLibraryItem[] {
    return this.visibleLibraryItems().filter((item) => item.path || item.favorite);
  }

  private applyFavorites(favorites: FavoriteSummary[]): void {
    this.favorites.set(favorites);
    const ids = new Set(favorites.map((item) => item.id));
    for (const item of favorites) this.tagDrafts[item.id] ??= tagsFor(item).join(", ");
    for (const id of Object.keys(this.tagDrafts).map(Number)) {
      if (!ids.has(id)) delete this.tagDrafts[id];
    }
  }

  private replaceFavorite(updated: FavoriteSummary): void {
    this.favorites.update((items) => items.map((item) => item.id === updated.id ? updated : item));
  }

  private recover<T>(source$: Observable<T>, fallback: T): Observable<T> {
    return source$.pipe(catchError((error) => {
      this.libraryError.set(errorMessage(error));
      return of(fallback);
    }));
  }

  private runOnce<T>(
    source$: Observable<T>,
    next: (value: T) => void,
    onError: (message: string) => void = () => undefined,
  ): void {
    source$.pipe(take(1), takeUntilDestroyed(this.destroyRef)).subscribe({
      next,
      error: (error) => {
        const message = errorMessage(error);
        this.libraryError.set(message);
        onError(message);
      },
    });
  }
}
