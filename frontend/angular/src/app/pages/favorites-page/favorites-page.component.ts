import {CommonModule} from "@angular/common";
import {Component, computed, inject, OnInit, signal} from "@angular/core";
import {FormsModule} from "@angular/forms";
import {Router} from "@angular/router";

import {ReadvideoApiService} from "../../services/readvideo-api.service";
import {FavoriteFolder, FavoriteSummary, TagSummary} from "../../types/readvideo.types";

@Component({
  selector: "rv-favorites-page",
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: "./favorites-page.component.html",
})
export class FavoritesPageComponent implements OnInit {
  private readonly api = inject(ReadvideoApiService);
  private readonly router = inject(Router);

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
    const active = this.activeFolderId();
    const activeTag = this.activeTag();
    const query = this.searchQuery().trim().toLowerCase();
    return this.favorites().filter((item) => {
      const inFolder = active === "all"
        || (active === "unfiled" && !item.folder_id)
        || String(item.folder_id) === active;
      if (!inFolder) return false;

      const tags = this.tagsFor(item);
      if (activeTag !== "all" && !this.hasTag(tags, activeTag)) return false;
      if (!query) return true;

      return [
        this.title(item),
        item.url,
        item.summary,
        item.markdown_path,
        item.notes_dir,
        item.folder_name,
        tags.join(" "),
      ].join(" ").toLowerCase().includes(query);
    });
  });

  readonly favoritesCount = computed(() => `${this.filteredFavorites().length} shown / ${this.favorites().length} saved`);

  ngOnInit(): void {
    void this.initialize();
  }

  async initialize(): Promise<void> {
    await Promise.all([this.loadFolders(), this.loadFavorites(), this.loadTags()]);
  }

  async loadFavorites(): Promise<void> {
    try {
      this.error.set("");
      const favorites = await this.api.favorites();
      this.favorites.set(favorites);
      this.syncTagDrafts(favorites);
    } catch (error) {
      this.error.set(this.message(error));
    }
  }

  async loadFolders(): Promise<void> {
    const folders = await this.api.favoriteFolders();
    this.folders.set(folders);
    this.syncFolderDrafts(folders);
  }

  async loadTags(): Promise<void> {
    this.tags.set(await this.api.tags());
  }

  setActiveFolder(id: string): void {
    this.activeFolderId.set(id);
  }

  setActiveTag(tag: string): void {
    this.activeTag.set(tag);
  }

  folderCount(id: string | number): number {
    if (id === "all") return this.favorites().length;
    if (id === "unfiled") return this.favorites().filter((item) => !item.folder_id).length;
    return this.favorites().filter((item) => item.folder_id === Number(id)).length;
  }

  tagCount(tag: string): number {
    if (tag === "all") return this.favorites().length;
    return this.favorites().filter((item) => this.hasTag(this.tagsFor(item), tag)).length;
  }

  folderId(folder: FavoriteFolder): string {
    return String(folder.id);
  }

  folderTags(id: string | number): string[] {
    const tags = new Set<string>();
    for (const item of this.favoritesForFolder(id)) {
      for (const tag of this.tagsFor(item)) {
        tags.add(tag);
      }
    }
    return [...tags].sort((first, second) => first.localeCompare(second, undefined, {sensitivity: "base"})).slice(0, 5);
  }

  folderInitial(folder: FavoriteFolder): string {
    return (folder.name.trim()[0] || "N").toUpperCase();
  }

  favoritesForFolder(id: string | number): FavoriteSummary[] {
    if (id === "all") return this.favorites();
    if (id === "unfiled") return this.favorites().filter((item) => !item.folder_id);
    return this.favorites().filter((item) => item.folder_id === Number(id));
  }

  async createFolder(): Promise<void> {
    try {
      await this.api.addFavoriteFolder(this.folderName.trim(), this.folderNotes.trim());
      this.folderName = "";
      this.folderNotes = "";
      this.notice.set("Folder created");
      await this.loadFolders();
    } catch (error) {
      this.error.set(this.message(error));
    }
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
    this.folderDrafts[folder.id] = {...(this.folderDrafts[folder.id] || {name: folder.name, notes: folder.notes}), name: value};
  }

  setFolderDraftNotes(folder: FavoriteFolder, value: string): void {
    this.folderDrafts[folder.id] = {...(this.folderDrafts[folder.id] || {name: folder.name, notes: folder.notes}), notes: value};
  }

  async saveFolder(folder: FavoriteFolder): Promise<void> {
    try {
      const draft = this.folderDrafts[folder.id] || {name: folder.name, notes: folder.notes};
      const updated = await this.api.updateFavoriteFolder(folder.id, draft.name.trim(), draft.notes.trim());
      this.folders.update((folders) => folders.map((item) => item.id === updated.id ? updated : item));
      this.folderDrafts[updated.id] = {name: updated.name, notes: updated.notes};
      this.editingFolderId.set(null);
      this.notice.set("Folder updated");
      await this.loadFavorites();
    } catch (error) {
      this.error.set(this.message(error));
    }
  }

  async deleteFolder(folder: FavoriteFolder): Promise<void> {
    await this.api.deleteFavoriteFolder(folder.id);
    this.activeFolderId.set("all");
    await Promise.all([this.loadFolders(), this.loadFavorites()]);
  }

  async assignFolder(item: FavoriteSummary, value: string): Promise<void> {
    try {
      const updated = await this.api.assignFavoriteFolder(item.id, value ? Number(value) : null);
      this.replaceFavorite(updated);
      await this.loadFolders();
    } catch (error) {
      this.error.set(this.message(error));
    }
  }

  async deleteFavorite(item: FavoriteSummary): Promise<void> {
    await this.api.deleteFavorite(item.id);
    delete this.tagDrafts[item.id];
    await Promise.all([this.loadFolders(), this.loadFavorites(), this.loadTags()]);
  }

  tagsFor(item: FavoriteSummary): string[] {
    return item.tags || [];
  }

  tagDraft(item: FavoriteSummary): string {
    if (!(item.id in this.tagDrafts)) {
      this.tagDrafts[item.id] = this.tagsFor(item).join(", ");
    }
    return this.tagDrafts[item.id];
  }

  setTagDraft(item: FavoriteSummary, value: string): void {
    this.tagDrafts[item.id] = value;
  }

  async saveTags(item: FavoriteSummary): Promise<void> {
    try {
      const updated = await this.api.updateFavoriteTags(item.id, this.parseTags(this.tagDraft(item)));
      this.replaceFavorite(updated);
      this.tagDrafts[item.id] = this.tagsFor(updated).join(", ");
      this.notice.set("Tags saved");
      await this.loadTags();
    } catch (error) {
      this.error.set(this.message(error));
    }
  }

  async readFavorite(item: FavoriteSummary): Promise<void> {
    if (item.markdown_path) {
      await this.openMarkdownPath(item.markdown_path);
      return;
    }
    try {
      const document = await this.api.favoriteMarkdown(item.id);
      await this.openMarkdownPath(document.path);
    } catch (error) {
      this.error.set(this.message(error));
    }
  }

  async openMarkdownPath(path: string): Promise<void> {
    await this.router.navigate(["/reader"], {queryParams: {path}});
  }

  async browseFolder(item: FavoriteSummary): Promise<void> {
    if (!item.notes_dir) return;
    await this.router.navigate(["/reader"], {queryParams: {folder: item.notes_dir}});
  }

  async openFolderInReader(id: string | number): Promise<void> {
    await this.router.navigate(["/reader"], {queryParams: {favoriteFolderId: String(id)}});
  }

  async copyFolderLabel(folder: FavoriteFolder): Promise<void> {
    try {
      await navigator.clipboard.writeText(folder.name);
      this.notice.set("Folder name copied");
    } catch (error) {
      this.error.set(this.message(error));
    }
  }

  title(item: FavoriteSummary): string {
    return item.title || item.url || item.task_id;
  }

  downloadHref(path: string): string {
    return `/api/markdown_files/download?path=${encodeURIComponent(path)}`;
  }

  private replaceFavorite(updated: FavoriteSummary): void {
    this.favorites.update((items) => items.map((item) => item.id === updated.id ? updated : item));
  }

  private syncTagDrafts(items: FavoriteSummary[]): void {
    const ids = new Set(items.map((item) => item.id));
    for (const item of items) {
      if (!(item.id in this.tagDrafts)) {
        this.tagDrafts[item.id] = this.tagsFor(item).join(", ");
      }
    }
    for (const key of Object.keys(this.tagDrafts)) {
      if (!ids.has(Number(key))) {
        delete this.tagDrafts[Number(key)];
      }
    }
  }

  private syncFolderDrafts(folders: FavoriteFolder[]): void {
    const ids = new Set(folders.map((folder) => folder.id));
    for (const folder of folders) {
      if (!(folder.id in this.folderDrafts)) {
        this.folderDrafts[folder.id] = {name: folder.name, notes: folder.notes};
      }
    }
    for (const key of Object.keys(this.folderDrafts)) {
      if (!ids.has(Number(key))) {
        delete this.folderDrafts[Number(key)];
      }
    }
  }

  private parseTags(value: string): string[] {
    return value
      .replace(/(^|\s)#/g, "$1,")
      .split(/[,;\n]+/)
      .map((tag) => tag.trim().replace(/^#/, ""))
      .filter(Boolean);
  }

  private hasTag(tags: string[], tag: string): boolean {
    const needle = tag.toLowerCase();
    return tags.some((item) => item.toLowerCase() === needle);
  }

  private message(error: unknown): string {
    return error instanceof Error ? error.message : String(error);
  }
}
