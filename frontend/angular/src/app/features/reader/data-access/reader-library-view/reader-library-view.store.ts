import {Injectable, computed, inject, signal} from "@angular/core";

import {LibraryStore} from "../../../library/data-access/library-store/library.store";
import {FavoriteFolder, MarkdownFile} from "../../../../shared/models/readvideo-types/readvideo.types";
import {tagsFor} from "../../../../shared/utils/tags/tags";
import {LibraryMode, LibrarySort, ReaderLibraryItem} from "../../models/reader-types/reader.types";
import {filterFavorites, filterFiles, libraryItems} from "../../utils/reader-library/reader-library";

@Injectable()
export class ReaderLibraryViewStore {
  private readonly library = inject(LibraryStore);

  readonly favorites = this.library.favorites;
  readonly folders = this.library.folders;
  readonly tags = this.library.tags;
  readonly files = signal<MarkdownFile[]>([]);
  readonly fileCount = signal("0 个文件");
  readonly activeFolderId = signal("all");
  readonly activeTag = signal("all");
  readonly searchQuery = signal("");
  readonly mode = signal<LibraryMode>("all");
  readonly sort = signal<LibrarySort>("recent");

  readonly filteredFavorites = computed(() => filterFavorites(
    this.favorites(),
    this.activeFolderId(),
    this.activeTag(),
    this.searchQuery(),
    this.sort(),
  ));
  readonly filteredFiles = computed(() => filterFiles(this.files(), this.searchQuery(), this.sort()));
  readonly visibleItems = computed(() => libraryItems(
    this.mode(),
    this.filteredFavorites(),
    this.filteredFiles(),
  ));
  readonly libraryCount = computed(() => `${this.filteredFavorites().length} 篇收藏 · ${this.fileCount()}`);
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
      for (const tag of tagsFor(item)) {
        const key = tag.toLocaleLowerCase();
        counts[key] = (counts[key] ?? 0) + 1;
      }
    }
    return counts;
  });
  readonly visibleTags = computed(() => this.tags().filter((tag) => this.tagCount(tag.name) > 0));

  showFiles(files: MarkdownFile[]): void {
    this.files.set(files);
    this.fileCount.set(`${files.length} 个文件`);
  }

  markFilesLoading(): void {
    this.fileCount.set("正在加载");
  }

  markFilesFailed(): void {
    this.files.set([]);
    this.fileCount.set("加载失败");
  }

  setMode(mode: LibraryMode): void {
    this.mode.set(mode);
  }

  setSearchQuery(query: string): void {
    this.searchQuery.set(query);
  }

  setActiveTag(tag: string): void {
    this.activeTag.set(tag);
  }

  setActiveFolder(id: string): void {
    const valid = id === "all" || id === "unfiled" || this.folders().some((folder) => String(folder.id) === id);
    this.activeFolderId.set(valid ? id : "all");
  }

  setSort(sort: string): void {
    if (["recent", "title", "folder", "path"].includes(sort)) this.sort.set(sort as LibrarySort);
  }

  availableItems(): ReaderLibraryItem[] {
    return this.visibleItems().filter((item) => item.path || item.favorite);
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
}
