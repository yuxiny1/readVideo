import {CommonModule} from "@angular/common";
import {ChangeDetectionStrategy, Component, inject} from "@angular/core";
import {FormsModule} from "@angular/forms";

import {TagChipComponent} from "../../../../shared/ui/tag-chip/tag-chip.component";
import {ReaderFacade} from "../../data-access/reader-facade/reader.facade";

@Component({
  selector: "rv-reader-library",
  standalone: true,
  imports: [CommonModule, FormsModule, TagChipComponent],
  templateUrl: "./reader-library.component.html",
  styleUrl: "./reader-library.component.scss",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ReaderLibraryComponent {
  readonly reader = inject(ReaderFacade);
}
