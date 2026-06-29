import {DomSanitizer, SafeHtml} from "@angular/platform-browser";
import {computed, inject} from "@angular/core";
import {tapResponse} from "@ngrx/operators";
import {patchState, signalStore, withComputed, withMethods, withState} from "@ngrx/signals";
import {rxMethod} from "@ngrx/signals/rxjs-interop";
import {concatMap, defer, pipe, switchMap, timer} from "rxjs";

import {MarkdownDocument} from "../../../../shared/models/readvideo-types/readvideo.types";
import {errorMessage} from "../../../../shared/utils/errors/errors";
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
  persistReaderTextSizeDefault,
  persistReaderWidthDefault,
  readFocusModeDefault,
  readFocusThemeDefault,
  readReaderTextSizeDefault,
  readReaderWidthDefault,
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
    status: "空闲",
    path: "",
    title: "选择一篇 Markdown 笔记",
    documentMeta: "左侧会显示收藏笔记和本地 Markdown 文件。",
    rawContent: "",
    emptyMessage: "请选择一篇笔记开始阅读。",
    documentQuery: "",
    error: "",
    focusMode: readFocusModeDefault(),
    focusTheme: readFocusThemeDefault(),
    readerWidth: readReaderWidthDefault(),
    readerTextSize: readReaderTextSizeDefault(),
    viewMode: "rendered",
  })),
  withComputed((store) => {
    const sanitizer = inject(DomSanitizer);
    return {
      headings: computed(() => extractHeadings(store.rawContent())),
      sourceUrl: computed(() => extractMetadata(store.rawContent(), "source")),
      generatedAt: computed(() => extractMetadata(store.rawContent(), "generated")),
      transcriptPath: computed(() => (
        extractMetadata(store.rawContent(), "transcript").replace(/^`|`$/g, "")
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
      status: "错误",
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
                patchState(store, {status: store.path() ? "已打开" : "空闲"});
              }
            },
            error: (error) => fail(errorMessage(error)),
          }),
        )),
      ),
    );

    return {
      beginOpen(path: string): void {
        patchState(store, {status: "正在加载", path, error: ""});
      },

      open(document: MarkdownDocument): void {
        patchState(store, {
          path: document.path,
          title: extractTitle(document.content) || fileName(document.path),
          rawContent: document.content,
          documentMeta: (
            `${fileName(document.path)} · ${readingStats(document.content)} · ${extractHeadings(document.content).length} 个章节`
          ),
          emptyMessage: "请选择一篇笔记开始阅读。",
          documentQuery: "",
          error: "",
          status: "已打开",
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
        persistReaderWidthDefault(readerWidth);
      },

      setReaderTextSize(readerTextSize: ReaderTextSize): void {
        patchState(store, {readerTextSize});
        persistReaderTextSizeDefault(readerTextSize);
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
        if (value) copyText({value, successStatus: "路径已复制"});
      },

      copyMarkdown(): void {
        const value = store.rawContent();
        if (value) copyText({value, successStatus: "完整 Markdown 已复制"});
      },

      downloadHref(path = store.path()): string {
        return `/api/markdown_files/download?path=${encodeURIComponent(path)}`;
      },
    };
  }),
);
