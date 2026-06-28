import {CommonModule} from "@angular/common";
import {ChangeDetectionStrategy, Component, inject, OnInit} from "@angular/core";
import {FormsModule} from "@angular/forms";
import {RouterLink} from "@angular/router";

import {ReaderFacade} from "./reader.facade";
import {ReaderDocumentStore} from "./reader-document.store";

@Component({
  selector: "rv-reader-page",
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: "./reader-page.component.html",
  providers: [ReaderDocumentStore, ReaderFacade],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ReaderPageComponent implements OnInit {
  readonly reader = inject(ReaderFacade);

  ngOnInit(): void {
    this.reader.initialize();
  }
}
