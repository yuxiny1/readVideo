import {DomSanitizer, SafeHtml} from "@angular/platform-browser";
import {computed, inject} from "@angular/core";
import {tapResponse} from "@ngrx/operators";
import {patchState, signalStore, withComputed, withMethods, withState} from "@ngrx/signals";
import {rxMethod} from "@ngrx/signals/rxjs-interop";
import {concatMap, defer, pipe, switchMap, timer} from "rxjs";

import {MarkdownDocument} from "../../../../shared/models/readvideo-types/readvideo.types";
import {errorMessage} from "../../../../shared/utils/errors/errors";
import {formatBytes} from "../../../../shared/utils/format/format";
import {
  countMatches,
  escapeHtml,
  extractHeadings,
  extractMetadata,
  extractTitle,
  fileName,
  readingStats,
  renderMarkdown,
} from "../../utils/reader-markdown/reader-markdown";
import {
  persistFocusModeDefault,
  persistFocusThemeDefault,
  readFocusModeDefault,
  readFocusThemeDefault,
} from "../../utils/reader-preferences/reader-preferences";
import {ReaderFocusTheme, ReaderTextSize, ReaderViewMode, ReaderWidth} from "../../models/reader-types/reader.types";

interface ReaderDocumentState {
  status: string;
  path: string;
  title: string;
  documentMeta: string;
  rawContent: string;
  emptyMessage: string;
  documentQuery: string;
  error: string;
  focusMode: boolean;
  focusTheme: ReaderFocusTheme;
  readerWidth: ReaderWidth;
  readerTextSize: ReaderTextSize;
  viewMode: ReaderViewMode;
}

interface CopyTextCommand {
  value: string;
  successStatus: string;
}

export const ReaderDocumentStore = signalStore(
  withState<ReaderDocumentState>(() => ({
    status: "Idle",
    path: "",
    title: "Choose a Markdown note",
    documentMeta: "Favorites and local Markdown files appear on the left.",
    rawContent: "",
    emptyMessage: "Pick a note to start reading.",
    documentQuery: "",
    error: "",
    focusMode: readFocusModeDefault(),
    focusTheme: readFocusThemeDefault(),
    readerWidth: "standard",
    readerTextSize: "standard",
    viewMode: "rendered",
  })),
  withComputed((store) => {
    const sanitizer = inject(DomSanitizer);
    return {
      headings: computed(() => extractHeadings(store.rawContent())),
      sourceUrl: computed(() => extractMetadata(store.rawContent(), "Source")),
      generatedAt: computed(() => extractMetadata(store.rawContent(), "Generated")),
      transcriptPath: computed(() => (
        extractMetadata(store.rawContent(), "Transcript").replace(/^`|`$/g, "")
      )),
      searchMatchCount: computed(() => countMatches(store.rawContent(), store.documentQuery())),
      html: computed<SafeHtml>(() => {
        const content = store.rawContent();
        const html = content
          ? renderMarkdown(content)
          : `<div class="reader-empty">${escapeHtml(store.emptyMessage())}</div>`;
        return sanitizer.bypassSecurityTrustHtml(html);
      }),
    };
  }),
  withMethods((store) => {
    const fail = (message: string) => patchState(store, {
      status: "Error",
      error: message,
      rawContent: "",
      emptyMessage: message,
    });
    const copyText = rxMethod<CopyTextCommand>(
      pipe(
        concatMap(({value, successStatus}) => defer(() => navigator.clipboard.writeText(value)).pipe(
          switchMap(() => {
            patchState(store, {status: successStatus});
            return timer(1200);
          }),
          tapResponse({
            next: () => {
              if (store.status() === successStatus) {
                patchState(store, {status: store.path() ? "Open" : "Idle"});
              }
            },
            error: (error) => fail(errorMessage(error)),
          }),
        )),
      ),
    );

    return {
      beginOpen(path: string): void {
        patchState(store, {status: "Loading", path, error: ""});
      },

      open(document: MarkdownDocument): void {
        patchState(store, {
          path: document.path,
          title: extractTitle(document.content) || fileName(document.path),
          rawContent: document.content,
          documentMeta: (
            `${fileName(document.path)} · ${readingStats(document.content)} · ${extractHeadings(document.content).length} sections`
          ),
          emptyMessage: "Pick a note to start reading.",
          documentQuery: "",
          error: "",
          status: "Open",
        });
      },

      fail,

      setStatus(status: string): void {
        patchState(store, {status});
      },

      setDocumentQuery(documentQuery: string): void {
        patchState(store, {documentQuery});
      },

      toggleFocusMode(): void {
        const focusMode = !store.focusMode();
        patchState(store, {focusMode});
        persistFocusModeDefault(focusMode);
      },

      setFocusTheme(focusTheme: ReaderFocusTheme): void {
        patchState(store, {focusTheme});
        persistFocusThemeDefault(focusTheme);
      },

      setReaderWidth(readerWidth: ReaderWidth): void {
        patchState(store, {readerWidth});
      },

      setReaderTextSize(readerTextSize: ReaderTextSize): void {
        patchState(store, {readerTextSize});
      },

      setViewMode(viewMode: ReaderViewMode): void {
        patchState(store, {viewMode});
      },

      scrollToHeading(id: string): void {
        document.getElementById(id)?.scrollIntoView({behavior: "smooth", block: "start"});
      },

      findInDocument(): void {
        const query = store.documentQuery().trim();
        if (!query) return;
        const finder = window as Window & {find?: (text: string) => boolean};
        finder.find?.(query);
      },

      copyPath(value = store.path()): void {
        if (value) copyText({value, successStatus: "Path copied"});
      },

      copyMarkdown(): void {
        const value = store.rawContent();
        if (value) copyText({value, successStatus: "Full Markdown copied"});
      },

      formatBytes(value: number): string {
        return formatBytes(value);
      },

      downloadHref(path = store.path()): string {
        return `/api/markdown_files/download?path=${encodeURIComponent(path)}`;
      },
    };
  }),
);
