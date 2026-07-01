import {CommonModule} from "@angular/common";
import {ChangeDetectionStrategy, Component, inject} from "@angular/core";

import {ReaderFacade} from "../../data-access/reader-facade/reader.facade";

@Component({
  selector: "rv-reader-inspector",
  standalone: true,
  imports: [CommonModule],
  templateUrl: "./reader-inspector.component.html",
  styleUrl: "./reader-inspector.component.scss",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ReaderInspectorComponent {
  readonly reader = inject(ReaderFacade);
}
