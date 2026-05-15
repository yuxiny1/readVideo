import {CommonModule} from "@angular/common";
import {Component, computed, inject, OnInit, signal} from "@angular/core";
import {FormsModule} from "@angular/forms";
import {Router} from "@angular/router";

import {ReadvideoApiService} from "../../services/readvideo-api.service";
import {formatBytes} from "../../shared/format";
import {FavoriteFolder, FavoriteSummary, MarkdownFile} from "../../types/readvideo.types";

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
  readonly activeFolderId = signal("all");
  readonly files = signal<MarkdownFile[]>([]);
  readonly defaultNotesDir = signal("notes");
  readonly error = signal("");
  readonly fileCount = signal("0 files");
  folderName = "";
  folderNotes = "";
  markdownFolder = "notes";

  readonly filteredFavorites = computed(() => {
    const active = this.activeFolderId();
    if (active === "all") return this.favorites();
    if (active === "unfiled") return this.favorites().filter((item) => !item.folder_id);
    return this.favorites().filter((item) => String(item.folder_id) === active);
  });

  readonly favoritesCount = computed(() => `${this.filteredFavorites().length} shown / ${this.favorites().length} saved`);

  ngOnInit(): void {
    void this.initialize();
  }

  async initialize(): Promise<void> {
    await this.loadConfig();
    await Promise.all([this.loadFolders(), this.loadFavorites()]);
    await this.loadMarkdownFiles(this.markdownFolder);
  }

  async loadConfig(): Promise<void> {
    try {
      const config = await this.api.appConfig();
      this.defaultNotesDir.set(config.notes_dir || "notes");
      this.markdownFolder ||= this.defaultNotesDir();
    } catch {
      this.markdownFolder = this.defaultNotesDir();
    }
  }

  async loadFavorites(): Promise<void> {
    try {
      this.error.set("");
      this.favorites.set(await this.api.favorites());
    } catch (error) {
      this.error.set(this.message(error));
    }
  }

  async loadFolders(): Promise<void> {
    this.folders.set(await this.api.favoriteFolders());
  }

  folderCount(id: string | number): number {
    if (id === "all") return this.favorites().length;
    if (id === "unfiled") return this.favorites().filter((item) => !item.folder_id).length;
    return this.favorites().filter((item) => item.folder_id === Number(id)).length;
  }

  folderId(folder: FavoriteFolder): string {
    return String(folder.id);
  }

  async createFolder(): Promise<void> {
    await this.api.addFavoriteFolder(this.folderName.trim(), this.folderNotes.trim());
    this.folderName = "";
    this.folderNotes = "";
    await this.loadFolders();
  }

  async deleteFolder(folder: FavoriteFolder): Promise<void> {
    await this.api.deleteFavoriteFolder(folder.id);
    this.activeFolderId.set("all");
    await Promise.all([this.loadFolders(), this.loadFavorites()]);
  }

  async assignFolder(item: FavoriteSummary, value: string): Promise<void> {
    await this.api.assignFavoriteFolder(item.id, value ? Number(value) : null);
    await Promise.all([this.loadFolders(), this.loadFavorites()]);
  }

  async deleteFavorite(item: FavoriteSummary): Promise<void> {
    await this.api.deleteFavorite(item.id);
    await Promise.all([this.loadFolders(), this.loadFavorites()]);
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

  async loadMarkdownFiles(directory = this.markdownFolder.trim() || this.defaultNotesDir()): Promise<void> {
    this.fileCount.set("Loading");
    try {
      const files = await this.api.markdownFiles(directory);
      this.markdownFolder = directory;
      this.files.set(files);
      this.fileCount.set(`${files.length} files`);
    } catch (error) {
      this.files.set([]);
      this.fileCount.set("Error");
      this.error.set(this.message(error));
    }
  }

  async readMarkdownFile(file: MarkdownFile): Promise<void> {
    await this.openMarkdownPath(file.path);
  }

  async openMarkdownPath(path: string): Promise<void> {
    await this.router.navigate(["/reader"], {queryParams: {path}});
  }

  showFolder(item: FavoriteSummary): void {
    this.markdownFolder = item.notes_dir;
    void this.loadMarkdownFiles(item.notes_dir);
  }

  title(item: FavoriteSummary): string {
    return item.title || item.url || item.task_id;
  }

  formatBytes(value: number): string {
    return formatBytes(value);
  }

  downloadHref(path: string): string {
    return `/api/markdown_files/download?path=${encodeURIComponent(path)}`;
  }

  private message(error: unknown): string {
    return error instanceof Error ? error.message : String(error);
  }
}
