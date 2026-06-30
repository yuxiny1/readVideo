import {CommonModule} from "@angular/common";
import {ChangeDetectionStrategy, Component, inject, OnInit} from "@angular/core";
import {FormsModule} from "@angular/forms";
import {RouterLink} from "@angular/router";

import {TagToneDirective} from "../../../../shared/ui/tag-tone/tag-tone.directive";
import {LibraryStore} from "../../../library/data-access/library-store/library.store";
import {ReaderDocumentStore} from "../../data-access/reader-document/reader-document.store";
import {ReaderFacade} from "../../data-access/reader-facade/reader.facade";

@Component({
  selector: "rv-reader-page",
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, TagToneDirective],
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
