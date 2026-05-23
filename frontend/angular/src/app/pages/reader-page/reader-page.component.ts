import {CommonModule} from "@angular/common";
import {Component, computed, inject, OnInit, signal} from "@angular/core";
import {FormsModule} from "@angular/forms";
import {ActivatedRoute, Router, RouterLink} from "@angular/router";
import {DomSanitizer, SafeHtml} from "@angular/platform-browser";

import {ReadvideoApiService} from "../../services/readvideo-api.service";
import {formatBytes} from "../../shared/format";
import {FavoriteFolder, FavoriteSummary, MarkdownFile} from "../../types/readvideo.types";

type LibraryMode = "all" | "favorites" | "files";
type LibrarySort = "recent" | "title" | "folder" | "path";
type ReaderWidth = "standard" | "wide";
type ReaderTextSize = "standard" | "large";
type ReaderViewMode = "rendered" | "markdown";
type ReaderFocusTheme = "light" | "dark";

const FOCUS_MODE_STORAGE_KEY = "readvideo.reader.focusMode";
const FOCUS_THEME_STORAGE_KEY = "readvideo.reader.focusTheme";

interface ReaderHeading {
  id: string;
  level: number;
  title: string;
}

interface ReaderLibraryItem {
  kind: "favorite" | "file";
  path: string;
  favorite?: FavoriteSummary;
  file?: MarkdownFile;
}

@Component({
  selector: "rv-reader-page",
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: "./reader-page.component.html",
})
export class ReaderPageComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(ReadvideoApiService);
  private readonly sanitizer = inject(DomSanitizer);

  readonly status = signal("Idle");
  readonly path = signal("");
  readonly title = signal("Choose a Markdown note");
  readonly documentMeta = signal("Favorites and local Markdown files appear on the left.");
  readonly rawContent = signal("");
  readonly emptyMessage = signal("Pick a note to start reading.");
  readonly favorites = signal<FavoriteSummary[]>([]);
  readonly folders = signal<FavoriteFolder[]>([]);
  readonly activeFolderId = signal("all");
  readonly files = signal<MarkdownFile[]>([]);
  readonly fileCount = signal("0 files");
  readonly defaultNotesDir = signal("notes");
  readonly error = signal("");
  readonly searchQuery = signal("");
  readonly documentQuery = signal("");
  readonly libraryMode = signal<LibraryMode>("all");
  readonly librarySort = signal<LibrarySort>("recent");
  readonly focusMode = signal(readFocusModeDefault());
  readonly focusTheme = signal<ReaderFocusTheme>(readFocusThemeDefault());
  readonly readerWidth = signal<ReaderWidth>("standard");
  readonly readerTextSize = signal<ReaderTextSize>("standard");
  readonly viewMode = signal<ReaderViewMode>("rendered");
  markdownFolder = "notes";

  readonly filteredFavorites = computed(() => {
    const active = this.activeFolderId();
    const query = this.searchQuery().trim().toLowerCase();
    const matches = this.favorites().filter((item) => {
      const inFolder = active === "all"
        || (active === "unfiled" && !item.folder_id)
        || String(item.folder_id) === active;
      if (!inFolder) return false;
      if (!query) return true;
      return [item.title, item.url, item.summary, item.markdown_path, item.folder_name]
        .join(" ")
        .toLowerCase()
        .includes(query);
    });
    return this.sortFavorites(matches);
  });
  readonly visibleFavoriteNotes = computed(() => this.filteredFavorites().slice(0, 3));

  readonly filteredFiles = computed(() => {
    const query = this.searchQuery().trim().toLowerCase();
    const matches = this.files().filter((file) => {
      if (!query) return true;
      return [file.name, file.path, file.modified_at]
        .join(" ")
        .toLowerCase()
        .includes(query);
    });
    return this.sortFiles(matches);
  });

  readonly visibleLibraryItems = computed<ReaderLibraryItem[]>(() => {
    const mode = this.libraryMode();
    const items: ReaderLibraryItem[] = [];
    if (mode === "all" || mode === "favorites") {
      items.push(...this.filteredFavorites().map((favorite) => ({
        kind: "favorite" as const,
        path: favorite.markdown_path || "",
        favorite,
      })));
    }
    if (mode === "all" || mode === "files") {
      items.push(...this.filteredFiles().map((file) => ({
        kind: "file" as const,
        path: file.path,
        file,
      })));
    }
    return items;
  });

  readonly libraryCount = computed(() => `${this.filteredFavorites().length} favorites · ${this.fileCount()}`);
  readonly headings = computed(() => this.extractHeadings(this.rawContent()));
  readonly sourceUrl = computed(() => this.extractMetadata("Source"));
  readonly generatedAt = computed(() => this.extractMetadata("Generated"));
  readonly transcriptPath = computed(() => this.extractMetadata("Transcript").replace(/^`|`$/g, ""));
  readonly searchMatchCount = computed(() => this.countMatches(this.rawContent(), this.documentQuery()));
  readonly html = computed<SafeHtml>(() => {
    const content = this.rawContent();
    const html = content
      ? this.renderMarkdown(content)
      : `<div class="reader-empty">${this.escapeHtml(this.emptyMessage())}</div>`;
    return this.sanitizer.bypassSecurityTrustHtml(html);
  });
  readonly canOpenPrevious = computed(() => this.activeLibraryIndex() > 0);
  readonly canOpenNext = computed(() => {
    const index = this.activeLibraryIndex();
    return index >= 0 && index < this.visibleLibraryItems().filter((item) => item.path || item.favorite).length - 1;
  });

  async ngOnInit(): Promise<void> {
    await this.initialize();
  }

  async initialize(): Promise<void> {
    await this.loadConfig();
    await Promise.all([this.loadFolders(), this.loadFavorites()]);
    const folder = this.route.snapshot.queryParamMap.get("folder") || this.markdownFolder;
    await this.loadMarkdownFiles(folder);
    const path = this.route.snapshot.queryParamMap.get("path");
    if (path) {
      await this.openPath(path, false);
    }
  }

  async loadConfig(): Promise<void> {
    try {
      const config = await this.api.appConfig();
      this.defaultNotesDir.set(config.notes_dir || "notes");
      this.markdownFolder = this.defaultNotesDir();
    } catch {
      this.markdownFolder = this.defaultNotesDir();
    }
  }

  async loadFavorites(): Promise<void> {
    try {
      this.favorites.set(await this.api.favorites());
    } catch (error) {
      this.error.set(this.message(error));
    }
  }

  async loadFolders(): Promise<void> {
    try {
      this.folders.set(await this.api.favoriteFolders());
    } catch (error) {
      this.error.set(this.message(error));
    }
  }

  async loadMarkdownFiles(directory = this.markdownFolder.trim() || this.defaultNotesDir(), updateRoute = false): Promise<void> {
    this.fileCount.set("Loading");
    try {
      const files = await this.api.markdownFiles(directory);
      this.markdownFolder = directory;
      this.files.set(files);
      this.fileCount.set(`${files.length} files`);
      if (updateRoute) {
        await this.router.navigate([], {
          relativeTo: this.route,
          queryParams: {folder: directory, path: null},
          queryParamsHandling: "merge",
        });
      }
    } catch (error) {
      this.files.set([]);
      this.fileCount.set("Error");
      this.error.set(this.message(error));
    }
  }

  async openFavorite(item: FavoriteSummary): Promise<void> {
    if (item.notes_dir && item.notes_dir !== this.markdownFolder) {
      await this.loadMarkdownFiles(item.notes_dir);
    }
    if (item.markdown_path) {
      await this.openPath(item.markdown_path);
      return;
    }
    try {
      const document = await this.api.favoriteMarkdown(item.id);
      await this.openPath(document.path);
    } catch (error) {
      this.error.set(this.message(error));
    }
  }

  async openFile(file: MarkdownFile): Promise<void> {
    await this.openPath(file.path);
  }

  async openPath(path: string, updateRoute = true): Promise<void> {
    this.status.set("Loading");
    this.path.set(path);
    this.error.set("");
    try {
      const document = await this.api.markdownDocument(path);
      this.path.set(document.path);
      this.title.set(this.extractTitle(document.content) || this.fileName(document.path));
      this.rawContent.set(document.content);
      this.documentMeta.set(`${this.fileName(document.path)} · ${this.readingStats(document.content)} · ${this.headings().length} sections`);
      this.emptyMessage.set("Pick a note to start reading.");
      this.documentQuery.set("");
      this.status.set("Open");
      if (updateRoute) {
        await this.router.navigate([], {
          relativeTo: this.route,
          queryParams: {path: document.path, folder: this.markdownFolder},
          queryParamsHandling: "merge",
        });
      }
    } catch (error) {
      this.status.set("Error");
      const message = this.message(error);
      this.error.set(message);
      this.rawContent.set("");
      this.emptyMessage.set(message);
    }
  }

  setLibraryMode(mode: LibraryMode): void {
    this.libraryMode.set(mode);
  }

  setLibrarySort(sort: string): void {
    if (["recent", "title", "folder", "path"].includes(sort)) {
      this.librarySort.set(sort as LibrarySort);
    }
  }

  setReaderWidth(width: ReaderWidth): void {
    this.readerWidth.set(width);
  }

  setReaderTextSize(size: ReaderTextSize): void {
    this.readerTextSize.set(size);
  }

  toggleFocusMode(): void {
    this.setFocusMode(!this.focusMode());
  }

  setFocusMode(enabled: boolean): void {
    this.focusMode.set(enabled);
    persistFocusModeDefault(enabled);
  }

  setFocusTheme(theme: ReaderFocusTheme): void {
    this.focusTheme.set(theme);
    persistFocusThemeDefault(theme);
  }

  setViewMode(mode: ReaderViewMode): void {
    this.viewMode.set(mode);
  }

  async openAdjacent(direction: -1 | 1): Promise<void> {
    const items = this.visibleLibraryItems().filter((item) => item.path || item.favorite);
    const currentIndex = this.activeLibraryIndex(items);
    const next = items[currentIndex + direction];
    if (!next) return;
    await this.openLibraryItem(next);
  }

  async openLibraryItem(item: ReaderLibraryItem): Promise<void> {
    if (item.kind === "favorite" && item.favorite) {
      await this.openFavorite(item.favorite);
      return;
    }
    if (item.kind === "file" && item.file) {
      await this.openFile(item.file);
    }
  }

  scrollToHeading(id: string): void {
    document.getElementById(id)?.scrollIntoView({behavior: "smooth", block: "start"});
  }

  findInDocument(): void {
    const query = this.documentQuery().trim();
    if (!query) return;
    const finder = window as Window & {find?: (text: string) => boolean};
    finder.find?.(query);
  }

  async copyPath(value = this.path()): Promise<void> {
    if (!value) return;
    await this.copyText(value, "Path copied");
  }

  async copyMarkdown(): Promise<void> {
    if (!this.rawContent()) return;
    await this.copyText(this.rawContent(), "Markdown copied");
  }

  folderCount(id: string | number): number {
    if (id === "all") return this.favorites().length;
    if (id === "unfiled") return this.favorites().filter((item) => !item.folder_id).length;
    return this.favorites().filter((item) => item.folder_id === Number(id)).length;
  }

  folderId(folder: FavoriteFolder): string {
    return String(folder.id);
  }

  titleFor(item: FavoriteSummary): string {
    return item.title || item.url || item.task_id;
  }

  isActivePath(path: string): boolean {
    return this.path() === path;
  }

  formatBytes(value: number): string {
    return formatBytes(value);
  }

  downloadHref(path = this.path()): string {
    return `/api/markdown_files/download?path=${encodeURIComponent(path)}`;
  }

  private activeLibraryIndex(items = this.visibleLibraryItems().filter((item) => item.path || item.favorite)): number {
    const currentPath = this.path();
    if (!currentPath) return -1;
    return items.findIndex((item) => item.path === currentPath);
  }

  private sortFavorites(items: FavoriteSummary[]): FavoriteSummary[] {
    const sort = this.librarySort();
    return [...items].sort((first, second) => {
      if (sort === "title") return this.compareText(this.titleFor(first), this.titleFor(second));
      if (sort === "folder") {
        return this.compareText(first.folder_name || "Unfiled", second.folder_name || "Unfiled")
          || this.compareText(this.titleFor(first), this.titleFor(second));
      }
      if (sort === "path") return this.compareText(first.markdown_path || "", second.markdown_path || "");
      return this.dateValue(second.updated_at || second.created_at) - this.dateValue(first.updated_at || first.created_at);
    });
  }

  private sortFiles(items: MarkdownFile[]): MarkdownFile[] {
    const sort = this.librarySort();
    return [...items].sort((first, second) => {
      if (sort === "title" || sort === "folder") return this.compareText(first.name, second.name);
      if (sort === "path") return this.compareText(first.path, second.path);
      return this.dateValue(second.modified_at) - this.dateValue(first.modified_at);
    });
  }

  private compareText(first: string, second: string): number {
    return first.localeCompare(second, undefined, {numeric: true, sensitivity: "base"});
  }

  private dateValue(value: string): number {
    const date = Date.parse(value);
    return Number.isNaN(date) ? 0 : date;
  }

  private extractMetadata(label: "Source" | "Generated" | "Transcript"): string {
    const match = this.rawContent().match(new RegExp(`^${label}:\\s*(.+)$`, "m"));
    return match ? match[1].trim() : "";
  }

  private extractHeadings(markdown: string): ReaderHeading[] {
    const headings: ReaderHeading[] = [];
    let index = 0;
    for (const line of markdown.split(/\r?\n/)) {
      const heading = line.match(/^(#{1,4})\s+(.+)$/);
      if (!heading) continue;
      index += 1;
      const level = heading[1].length;
      if (level > 3) continue;
      headings.push({
        id: `section-${index}`,
        level,
        title: this.stripMarkdown(heading[2]),
      });
    }
    return headings;
  }

  private countMatches(content: string, query: string): number {
    const needle = query.trim().toLowerCase();
    if (!content || !needle) return 0;
    let count = 0;
    let position = 0;
    const haystack = content.toLowerCase();
    while ((position = haystack.indexOf(needle, position)) !== -1) {
      count += 1;
      position += needle.length;
    }
    return count;
  }

  private async copyText(value: string, successStatus: string): Promise<void> {
    try {
      await navigator.clipboard.writeText(value);
      this.status.set(successStatus);
      window.setTimeout(() => {
        if (this.status() === successStatus) this.status.set(this.path() ? "Open" : "Idle");
      }, 1200);
    } catch (error) {
      this.status.set("Error");
      this.error.set(this.message(error));
    }
  }

  private renderMarkdown(markdown: string): string {
    const lines = markdown.split(/\r?\n/);
    const html: string[] = [];
    let inList: "ul" | "ol" | null = null;
    let inCode = false;
    let codeLines: string[] = [];
    let headingIndex = 0;

    const closeList = () => {
      if (inList) {
        html.push(`</${inList}>`);
        inList = null;
      }
    };
    const openList = (kind: "ul" | "ol") => {
      if (inList === kind) return;
      closeList();
      html.push(`<${kind}>`);
      inList = kind;
    };
    const closeCode = () => {
      html.push(`<pre><code>${this.escapeHtml(codeLines.join("\n"))}</code></pre>`);
      codeLines = [];
      inCode = false;
    };

    for (const rawLine of lines) {
      const line = rawLine.trimEnd();
      if (line.trim().startsWith("```")) {
        if (inCode) closeCode();
        else {
          closeList();
          inCode = true;
        }
        continue;
      }
      if (inCode) {
        codeLines.push(rawLine);
        continue;
      }
      if (!line.trim()) {
        closeList();
        continue;
      }

      const heading = line.match(/^(#{1,4})\s+(.+)$/);
      if (heading) {
        closeList();
        const level = heading[1].length;
        headingIndex += 1;
        html.push(`<h${level} id="section-${headingIndex}">${this.inlineMarkdown(heading[2])}</h${level}>`);
        continue;
      }

      if (/^---+$/.test(line.trim())) {
        closeList();
        html.push("<hr>");
        continue;
      }

      const quote = line.match(/^>\s+(.+)$/);
      if (quote) {
        closeList();
        html.push(`<blockquote>${this.inlineMarkdown(quote[1])}</blockquote>`);
        continue;
      }

      const bullet = line.match(/^[-*]\s+(.+)$/);
      if (bullet) {
        openList("ul");
        html.push(`<li>${this.inlineMarkdown(bullet[1])}</li>`);
        continue;
      }

      const numbered = line.match(/^\d+[.)]\s+(.+)$/);
      if (numbered) {
        openList("ol");
        html.push(`<li>${this.inlineMarkdown(numbered[1])}</li>`);
        continue;
      }

      closeList();
      html.push(`<p>${this.inlineMarkdown(line)}</p>`);
    }

    closeList();
    if (inCode) closeCode();
    return html.join("");
  }

  private inlineMarkdown(value: string): string {
    return this.escapeHtml(value)
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/\*([^*]+)\*/g, "<em>$1</em>");
  }

  private extractTitle(markdown: string): string {
    const heading = markdown.match(/^#\s+(.+)$/m);
    return heading ? heading[1].trim() : "";
  }

  private stripMarkdown(value: string): string {
    return value
      .replace(/`([^`]+)`/g, "$1")
      .replace(/\*\*([^*]+)\*\*/g, "$1")
      .replace(/\*([^*]+)\*/g, "$1")
      .trim();
  }

  private fileName(path: string): string {
    return path.split(/[\\/]/).filter(Boolean).pop() || path || "Markdown note";
  }

  private readingStats(content: string): string {
    const words = content.trim().split(/\s+/).filter(Boolean).length;
    const cjkChars = (content.match(/[\u4e00-\u9fff]/g) || []).length;
    const units = Math.max(words, Math.ceil(cjkChars / 2));
    const minutes = Math.max(1, Math.ceil(units / 260));
    return `${minutes} min read`;
  }

  private escapeHtml(value: string): string {
    return value.replace(/[&<>"']/g, (char) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[char] || char));
  }

  private message(error: unknown): string {
    return error instanceof Error ? error.message : String(error);
  }
}


function readFocusModeDefault(): boolean {
  try {
    return localStorage.getItem(FOCUS_MODE_STORAGE_KEY) === "true";
  } catch {
    return false;
  }
}


function persistFocusModeDefault(enabled: boolean): void {
  try {
    localStorage.setItem(FOCUS_MODE_STORAGE_KEY, enabled ? "true" : "false");
  } catch {
    // Ignore private browsing or storage-disabled environments.
  }
}


function readFocusThemeDefault(): ReaderFocusTheme {
  try {
    return localStorage.getItem(FOCUS_THEME_STORAGE_KEY) === "dark" ? "dark" : "light";
  } catch {
    return "light";
  }
}


function persistFocusThemeDefault(theme: ReaderFocusTheme): void {
  try {
    localStorage.setItem(FOCUS_THEME_STORAGE_KEY, theme);
  } catch {
    // Ignore private browsing or storage-disabled environments.
  }
}
