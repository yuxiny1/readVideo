import {CommonModule} from "@angular/common";
import {ChangeDetectionStrategy, Component, inject, OnInit} from "@angular/core";
import {FormsModule} from "@angular/forms";
import {RouterLink} from "@angular/router";

import {LibraryStore} from "../../features/library/data-access/library.store";
import {ReaderFacade} from "./reader.facade";
import {ReaderDocumentStore} from "./reader-document.store";

@Component({
  selector: "rv-reader-page",
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: "./reader-page.component.html",
  providers: [LibraryStore, ReaderDocumentStore, ReaderFacade],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ReaderPageComponent implements OnInit {
  readonly reader = inject(ReaderFacade);

  ngOnInit(): void {
    this.reader.initialize();
  }
}
