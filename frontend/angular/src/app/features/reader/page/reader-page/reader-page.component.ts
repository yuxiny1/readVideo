import {CommonModule} from "@angular/common";
import {ChangeDetectionStrategy, Component, computed, HostListener, inject, OnInit} from "@angular/core";
import {RouterLink} from "@angular/router";

import {LibraryStore} from "../../../library/data-access/library-store/library.store";
import {ReaderDocumentStore} from "../../data-access/reader-document/reader-document.store";
import {ReaderFacade} from "../../data-access/reader-facade/reader.facade";
import {ReaderHistoryContextService} from "../../data-access/reader-history-context/reader-history-context.service";
import {ReaderDocumentComponent} from "../../ui/reader-document/reader-document.component";
import {ReaderInspectorComponent} from "../../ui/reader-inspector/reader-inspector.component";
import {ReaderLibraryComponent} from "../../ui/reader-library/reader-library.component";

@Component({
  selector: "rv-reader-page",
  standalone: true,
  imports: [CommonModule, RouterLink, ReaderLibraryComponent, ReaderDocumentComponent, ReaderInspectorComponent],
  templateUrl: "./reader-page.component.html",
  styleUrl: "./reader-page.component.scss",
  providers: [LibraryStore, ReaderDocumentStore, ReaderHistoryContextService, ReaderFacade],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ReaderPageComponent implements OnInit {
  readonly reader = inject(ReaderFacade);
  readonly pageVm = computed(() => {
    const document = this.reader.document;
    const status = document.status();
    const focusMode = document.focusMode();
    const focusDark = focusMode && document.focusTheme() === "dark";
    const hasDocument = Boolean(document.path());
    return {
      status,
      statusClass: status === "已打开" ? "ok" : status === "错误" ? "error" : "muted",
      libraryCount: this.reader.libraryCount(),
      focusMode,
      focusDark,
      wideLayout: document.readerWidth() === "wide",
      canToggleFocus: focusMode || hasDocument,
      canOpenPrevious: this.reader.canOpenPrevious(),
      canOpenNext: this.reader.canOpenNext(),
      focusButtonLabel: focusMode ? "退出专注阅读" : "进入专注阅读",
    };
  });

  ngOnInit(): void {
    this.reader.initialize();
  }

  @HostListener("document:keydown.escape")
  exitFocusMode(): void {
    if (this.reader.document.focusMode()) this.reader.document.toggleFocusMode();
  }
}
