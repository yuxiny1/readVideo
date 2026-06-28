import {DomSanitizer, SafeHtml} from "@angular/platform-browser";
import {DestroyRef, Injectable, computed, inject, signal} from "@angular/core";
import {takeUntilDestroyed} from "@angular/core/rxjs-interop";
import {defer, switchMap, take, timer} from "rxjs";

import {errorMessage} from "../../shared/errors";
import {formatBytes} from "../../shared/format";
import {MarkdownDocument} from "../../types/readvideo.types";
import {
  countMatches,
  escapeHtml,
  extractHeadings,
  extractMetadata,
  extractTitle,
  fileName,
  readingStats,
  renderMarkdown,
} from "./reader-markdown";
import {
  persistFocusModeDefault,
  persistFocusThemeDefault,
  readFocusModeDefault,
  readFocusThemeDefault,
} from "./reader-preferences";
import {ReaderFocusTheme, ReaderTextSize, ReaderViewMode, ReaderWidth} from "./reader.types";

@Injectable()
export class ReaderDocumentStore {
  private readonly sanitizer = inject(DomSanitizer);
  private readonly destroyRef = inject(DestroyRef);

  readonly status = signal("Idle");
  readonly path = signal("");
  readonly title = signal("Choose a Markdown note");
  readonly documentMeta = signal("Favorites and local Markdown files appear on the left.");
  readonly rawContent = signal("");
  readonly emptyMessage = signal("Pick a note to start reading.");
  readonly documentQuery = signal("");
  readonly error = signal("");
  readonly focusMode = signal(readFocusModeDefault());
  readonly focusTheme = signal<ReaderFocusTheme>(readFocusThemeDefault());
  readonly readerWidth = signal<ReaderWidth>("standard");
  readonly readerTextSize = signal<ReaderTextSize>("standard");
  readonly viewMode = signal<ReaderViewMode>("rendered");

  readonly headings = computed(() => extractHeadings(this.rawContent()));
  readonly sourceUrl = computed(() => extractMetadata(this.rawContent(), "Source"));
  readonly generatedAt = computed(() => extractMetadata(this.rawContent(), "Generated"));
  readonly transcriptPath = computed(() => (
    extractMetadata(this.rawContent(), "Transcript").replace(/^`|`$/g, "")
  ));
  readonly searchMatchCount = computed(() => countMatches(this.rawContent(), this.documentQuery()));
  readonly html = computed<SafeHtml>(() => {
    const content = this.rawContent();
    const html = content
      ? renderMarkdown(content)
      : `<div class="reader-empty">${escapeHtml(this.emptyMessage())}</div>`;
    return this.sanitizer.bypassSecurityTrustHtml(html);
  });

  beginOpen(path: string): void {
    this.status.set("Loading");
    this.path.set(path);
    this.error.set("");
  }

  open(document: MarkdownDocument): void {
    this.path.set(document.path);
    this.title.set(extractTitle(document.content) || fileName(document.path));
    this.rawContent.set(document.content);
    this.documentMeta.set(
      `${fileName(document.path)} · ${readingStats(document.content)} · ${extractHeadings(document.content).length} sections`,
    );
    this.emptyMessage.set("Pick a note to start reading.");
    this.documentQuery.set("");
    this.error.set("");
    this.status.set("Open");
  }

  fail(message: string): void {
    this.status.set("Error");
    this.error.set(message);
    this.rawContent.set("");
    this.emptyMessage.set(message);
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

  setReaderWidth(width: ReaderWidth): void {
    this.readerWidth.set(width);
  }

  setReaderTextSize(size: ReaderTextSize): void {
    this.readerTextSize.set(size);
  }

  setViewMode(mode: ReaderViewMode): void {
    this.viewMode.set(mode);
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

  copyPath(value = this.path()): void {
    if (value) this.copyText(value, "Path copied");
  }

  copyMarkdown(): void {
    if (this.rawContent()) this.copyText(this.rawContent(), "Full Markdown copied");
  }

  formatBytes(value: number): string {
    return formatBytes(value);
  }

  downloadHref(path = this.path()): string {
    return `/api/markdown_files/download?path=${encodeURIComponent(path)}`;
  }

  private copyText(value: string, successStatus: string): void {
    defer(() => navigator.clipboard.writeText(value)).pipe(
      switchMap(() => {
        this.status.set(successStatus);
        return timer(1200);
      }),
      take(1),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: () => {
        if (this.status() === successStatus) this.status.set(this.path() ? "Open" : "Idle");
      },
      error: (error) => this.fail(errorMessage(error)),
    });
  }
}
