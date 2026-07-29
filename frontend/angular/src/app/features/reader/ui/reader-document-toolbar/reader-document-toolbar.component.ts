import {CommonModule} from "@angular/common";
import {ChangeDetectionStrategy, Component, input} from "@angular/core";
import {FormsModule} from "@angular/forms";

import {TagChipComponent} from "../../../../shared/ui/tag-chip/tag-chip.component";
import {TagEditorComponent} from "../../../../shared/ui/tag-editor/tag-editor.component";
import {ReaderFacade} from "../../data-access/reader-facade/reader.facade";

@Component({
  selector: "rv-reader-document-toolbar",
  standalone: true,
  imports: [CommonModule, FormsModule, TagChipComponent, TagEditorComponent],
  templateUrl: "./reader-document-toolbar.component.html",
  styleUrl: "./reader-document-toolbar.component.scss",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ReaderDocumentToolbarComponent {
  readonly reader = input.required<ReaderFacade>();
}
