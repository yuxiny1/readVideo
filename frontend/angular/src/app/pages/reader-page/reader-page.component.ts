import {CommonModule} from "@angular/common";
import {Component, computed, inject, OnInit, signal} from "@angular/core";
import {FormsModule} from "@angular/forms";
import {ActivatedRoute, Router, RouterLink} from "@angular/router";
import {DomSanitizer, SafeHtml} from "@angular/platform-browser";

import {ReadvideoApiService} from "../../services/readvideo-api.service";
import {formatBytes} from "../../shared/format";
import {FavoriteFolder, FavoriteSummary, MarkdownFile} from "../../types/readvideo.types";

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
  readonly html = signal<SafeHtml>(this.sanitizer.bypassSecurityTrustHtml('<div class="reader-empty">Pick a note to start reading.</div>'));
  readonly favorites = signal<FavoriteSummary[]>([]);
  readonly folders = signal<FavoriteFolder[]>([]);
  readonly activeFolderId = signal("all");
  readonly files = signal<MarkdownFile[]>([]);
  readonly fileCount = signal("0 files");
  readonly defaultNotesDir = signal("notes");
  readonly error = signal("");
  readonly searchQuery = signal("");
  markdownFolder = "notes";

  readonly filteredFavorites = computed(() => {
    const active = this.activeFolderId();
    const query = this.searchQuery().trim().toLowerCase();
    return this.favorites().filter((item) => {
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
  });

  readonly libraryCount = computed(() => `${this.filteredFavorites().length} favorites · ${this.fileCount()}`);

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
      this.documentMeta.set(`${this.fileName(document.path)} · ${this.readingStats(document.content)}`);
      this.html.set(this.sanitizer.bypassSecurityTrustHtml(this.renderMarkdown(document.content)));
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
      this.html.set(this.sanitizer.bypassSecurityTrustHtml(`<div class="reader-empty">${this.escapeHtml(message)}</div>`));
    }
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

  private renderMarkdown(markdown: string): string {
    const lines = markdown.split(/\r?\n/);
    const html: string[] = [];
    let inList: "ul" | "ol" | null = null;
    let inCode = false;
    let codeLines: string[] = [];

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
        html.push(`<h${level}>${this.inlineMarkdown(heading[2])}</h${level}>`);
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
