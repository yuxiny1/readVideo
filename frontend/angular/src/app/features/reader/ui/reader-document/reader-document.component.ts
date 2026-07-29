import {ChangeDetectionStrategy, Component, input} from "@angular/core";

import {ReaderFacade} from "../../data-access/reader-facade/reader.facade";
import {ReaderContentComponent} from "../reader-content/reader-content.component";
import {ReaderDocumentToolbarComponent} from "../reader-document-toolbar/reader-document-toolbar.component";

@Component({
  selector: "rv-reader-document",
  standalone: true,
  imports: [ReaderContentComponent, ReaderDocumentToolbarComponent],
  templateUrl: "./reader-document.component.html",
  styleUrl: "./reader-document.component.scss",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ReaderDocumentComponent {
  readonly reader = input.required<ReaderFacade>();
}
