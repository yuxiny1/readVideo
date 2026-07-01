import {CommonModule} from "@angular/common";
import {ChangeDetectionStrategy, Component, inject} from "@angular/core";
import {FormsModule} from "@angular/forms";

import {ReaderFacade} from "../../data-access/reader-facade/reader.facade";

@Component({
  selector: "rv-reader-content",
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: "./reader-content.component.html",
  styleUrl: "./reader-content.component.scss",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ReaderContentComponent {
  readonly reader = inject(ReaderFacade);
}
