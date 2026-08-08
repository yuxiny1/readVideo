import {DestroyRef, Injectable, computed, effect, inject, signal} from "@angular/core";
import {takeUntilDestroyed} from "@angular/core/rxjs-interop";
import {ActivatedRoute, Router} from "@angular/router";
import {EMPTY, Observable, Subject, catchError, of, switchMap, take, tap} from "rxjs";

import {ReadvideoApiService} from "../../../../core/api/readvideo-api/readvideo-api.service";
import {LibraryStore} from "../../../library/data-access/library-store/library.store";
import {errorMessage} from "../../../../shared/utils/errors/errors";
import {
  FavoriteFolder,
  FavoriteSummary,
  MarkdownDocument,
  MarkdownFile,
} from "../../../../shared/models/readvideo-types/readvideo.types";
import {LibraryMode, ReaderLibraryItem} from "../../models/reader-types/reader.types";
import {ReaderDocumentStore} from "../reader-document/reader-document.store";
import {ReaderLibraryViewStore} from "../reader-library-view/reader-library-view.store";
import {ReaderTagEditorService} from "../reader-tag-editor/reader-tag-editor.service";

type DocumentRequest =
  | {kind: "path"; path: string; updateRoute: boolean}
  | {kind: "favorite"; itemId: number; updateRoute: boolean};

@Injectable()
export class ReaderFacade {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(ReadvideoApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly libraryView = inject(ReaderLibraryViewStore);
  private readonly tagEditor = inject(ReaderTagEditorService);
  private readonly markdownFileRequests = new Subject<{directory: string; updateRoute: boolean}>();
  private readonly documentRequests = new Subject<DocumentRequest>();
  readonly document = inject(ReaderDocumentStore);
  readonly library = inject(LibraryStore);

  readonly favorites = this.libraryView.favorites;
  readonly folders = this.libraryView.folders;
  readonly tags = this.libraryView.tags;
  readonly activeFolderId = this.libraryView.activeFolderId;
  readonly activeTag = this.libraryView.activeTag;
  readonly selectedFavoriteId = this.tagEditor.selectedFavoriteId;
  readonly activeTask = this.tagEditor.activeTask;
  readonly files = this.libraryView.files;
  readonly fileCount = this.libraryView.fileCount;
  readonly defaultNotesDir = signal("notes");
  readonly localError = signal("");
  readonly configReady = signal(false);
  readonly error = computed(() => (
    this.document.error() || this.localError() || this.tagEditor.error() || this.library.error()
  ));
  readonly searchQuery = this.libraryView.searchQuery;
  readonly libraryMode = this.libraryView.mode;
  readonly librarySort = this.libraryView.sort;
  markdownFolder = "notes";

  readonly filteredFavorites = this.libraryView.filteredFavorites;
  readonly filteredFiles = this.libraryView.filteredFiles;
  readonly visibleLibraryItems = this.libraryView.visibleItems;
  readonly libraryCount = this.libraryView.libraryCount;
  readonly activeFavorite = this.tagEditor.activeFavorite;
  readonly activeDocumentTags = this.tagEditor.activeTags;
  readonly activeDocumentIsTaggable = this.tagEditor.canEdit;
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
  readonly folderCounts = this.libraryView.folderCounts;
  readonly tagCounts = this.libraryView.tagCounts;
  readonly visibleTags = this.libraryView.visibleTags;
  private initialRouteApplied = false;
  constructor() {
    effect(() => {
      const ready = this.configReady() && !this.library.loading();
      if (!ready || this.initialRouteApplied) return;
      this.initialRouteApplied = true;
      this.applyInitialRoute();
    });
    this.markdownFileRequests.pipe(
      switchMap(({directory, updateRoute}) => this.api.markdownFiles(directory).pipe(
        tap((files) => {
          this.markdownFolder = directory;
          this.libraryView.showFiles(files);
          if (updateRoute) {
            void this.router.navigate([], {
              relativeTo: this.route,
              queryParams: {folder: directory, path: null},
              queryParamsHandling: "merge",
            });
          }
        }),
        catchError((error) => {
          this.localError.set(errorMessage(error));
          this.libraryView.markFilesFailed();
          return EMPTY;
        }),
      )),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe();

    this.documentRequests.pipe(
      switchMap((request) => {
        const document$ = request.kind === "favorite"
          ? this.api.favoriteMarkdown(request.itemId)
          : this.api.markdownDocument(request.path);
        return document$.pipe(
          tap((document) => this.applyDocument(document, request.updateRoute)),
          catchError((error) => {
            const message = errorMessage(error);
            this.localError.set(message);
            this.document.fail(message);
            return EMPTY;
          }),
        );
      }),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe();
  }

  initialize(): void {
    this.localError.set("");
    this.library.loadAll();
    this.runOnce(
      this.recover(this.api.appConfig(), null),
      (config) => {
        this.defaultNotesDir.set(config?.notes_dir || "notes");
        this.markdownFolder = this.defaultNotesDir();
        this.configReady.set(true);
      },
    );
  }

  loadMarkdownFiles(
    directory = this.markdownFolder.trim() || this.defaultNotesDir(),
    updateRoute = false,
  ): void {
    this.libraryView.markFilesLoading();
    this.markdownFileRequests.next({directory, updateRoute});
  }

  openFavorite(item: FavoriteSummary): void {
    this.tagEditor.selectFavorite(item);
    if (item.notes_dir && item.notes_dir !== this.markdownFolder) this.loadMarkdownFiles(item.notes_dir);
    this.document.beginOpen(item.markdown_path || item.title);
    this.localError.set("");
    this.documentRequests.next({kind: "favorite", itemId: item.id, updateRoute: true});
  }

  openFile(file: MarkdownFile): void {
    this.openPath(file.path);
  }

  openPath(path: string, updateRoute = true, taskId = ""): void {
    const matchingFavorite = this.tagEditor.selectPath(path);
    if (matchingFavorite) this.tagEditor.clearHistory();
    else if (taskId) this.tagEditor.loadHistory(taskId);
    else this.tagEditor.clearHistory();
    this.document.beginOpen(path);
    this.localError.set("");
    this.documentRequests.next({kind: "path", path, updateRoute});
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
    this.libraryView.setMode(mode);
  }

  setSearchQuery(query: string): void {
    this.libraryView.setSearchQuery(query);
  }

  setActiveTag(tag: string): void {
    this.libraryView.setActiveTag(tag);
  }

  setActiveFavoriteFolder(id: string): void {
    this.libraryView.setActiveFolder(id);
  }

  setLibrarySort(sort: string): void {
    this.libraryView.setSort(sort);
  }

  activeTagDraft(): string {
    return this.tagEditor.activeDraft();
  }

  setActiveTagDraft(value: string): void {
    this.tagEditor.setActiveDraft(value);
  }

  saveActiveTags(): void {
    this.tagEditor.saveActiveTags();
  }

  folderCount(id: string | number): number {
    return this.libraryView.folderCount(id);
  }

  tagCount(tag: string): number {
    return this.libraryView.tagCount(tag);
  }

  folderId(folder: FavoriteFolder): string {
    return this.libraryView.folderId(folder);
  }

  tagDraft(item: FavoriteSummary): string {
    return this.tagEditor.favoriteDraft(item);
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
    const taskId = this.route.snapshot.queryParamMap.get("taskId") || "";
    if (path) this.openPath(path, false, taskId);
  }

  private applyDocument(document: MarkdownDocument, updateRoute: boolean): void {
    this.document.open(document);
    if (updateRoute) {
      const activeTaskId = this.activeTask()?.task_id;
      void this.router.navigate([], {
        relativeTo: this.route,
        queryParams: {path: document.path, folder: this.markdownFolder, taskId: activeTaskId || null},
        queryParamsHandling: "merge",
      });
    }
  }

  private availableLibraryItems(): ReaderLibraryItem[] {
    return this.libraryView.availableItems();
  }

  private recover<T>(source$: Observable<T>, fallback: T): Observable<T> {
    return source$.pipe(catchError((error) => {
      this.localError.set(errorMessage(error));
      return of(fallback);
    }));
  }

  private runOnce<T>(
    source$: Observable<T>,
    next: (value: T) => void,
  ): void {
    source$.pipe(take(1), takeUntilDestroyed(this.destroyRef)).subscribe({
      next,
      error: (error) => {
        const message = errorMessage(error);
        this.localError.set(message);
      },
    });
  }
}
