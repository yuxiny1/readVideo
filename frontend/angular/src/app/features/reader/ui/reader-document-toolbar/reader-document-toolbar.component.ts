import {CommonModule} from "@angular/common";
import {ChangeDetectionStrategy, Component, inject} from "@angular/core";
import {FormsModule} from "@angular/forms";

import {TagChipComponent} from "../../../../shared/ui/tag-chip/tag-chip.component";
import {ReaderFacade} from "../../data-access/reader-facade/reader.facade";

@Component({
  selector: "rv-reader-document-toolbar",
  standalone: true,
  imports: [CommonModule, FormsModule, TagChipComponent],
  templateUrl: "./reader-document-toolbar.component.html",
  styleUrl: "./reader-document-toolbar.component.scss",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ReaderDocumentToolbarComponent {
  readonly reader = inject(ReaderFacade);
}
