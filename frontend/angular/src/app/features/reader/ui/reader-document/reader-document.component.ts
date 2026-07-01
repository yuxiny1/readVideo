import {ChangeDetectionStrategy, Component} from "@angular/core";

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
export class ReaderDocumentComponent {}
