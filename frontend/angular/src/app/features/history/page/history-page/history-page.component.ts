import {CommonModule} from "@angular/common";
import {ChangeDetectionStrategy, Component, inject, OnInit} from "@angular/core";
import {FormsModule} from "@angular/forms";

import {TagToneDirective} from "../../../../shared/ui/tag-tone/tag-tone.directive";
import {HistoryFacade} from "../../data-access/history-facade/history.facade";

@Component({
  selector: "rv-history-page",
  standalone: true,
  imports: [CommonModule, FormsModule, TagToneDirective],
  templateUrl: "./history-page.component.html",
  styleUrl: "./history-page.component.scss",
  providers: [HistoryFacade],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HistoryPageComponent implements OnInit {
  readonly history = inject(HistoryFacade);

  ngOnInit(): void {
    this.history.initialize();
  }
}
