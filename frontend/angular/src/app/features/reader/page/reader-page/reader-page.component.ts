import {CommonModule} from "@angular/common";
import {ChangeDetectionStrategy, Component, inject, OnInit} from "@angular/core";
import {RouterLink} from "@angular/router";

import {LibraryStore} from "../../../library/data-access/library-store/library.store";
import {ReaderDocumentStore} from "../../data-access/reader-document/reader-document.store";
import {ReaderFacade} from "../../data-access/reader-facade/reader.facade";
import {ReaderDocumentComponent} from "../../ui/reader-document/reader-document.component";
import {ReaderInspectorComponent} from "../../ui/reader-inspector/reader-inspector.component";
import {ReaderLibraryComponent} from "../../ui/reader-library/reader-library.component";

@Component({
  selector: "rv-reader-page",
  standalone: true,
  imports: [CommonModule, RouterLink, ReaderLibraryComponent, ReaderDocumentComponent, ReaderInspectorComponent],
  templateUrl: "./reader-page.component.html",
  styleUrl: "./reader-page.component.scss",
  providers: [LibraryStore, ReaderDocumentStore, ReaderFacade],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ReaderPageComponent implements OnInit {
  readonly reader = inject(ReaderFacade);

  ngOnInit(): void {
    this.reader.initialize();
  }
}
