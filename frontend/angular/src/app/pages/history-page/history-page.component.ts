import {CommonModule} from "@angular/common";
import {ChangeDetectionStrategy, Component, inject, OnInit} from "@angular/core";
import {FormsModule} from "@angular/forms";

import {HistoryFacade} from "./history.facade";

@Component({
  selector: "rv-history-page",
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: "./history-page.component.html",
  providers: [HistoryFacade],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HistoryPageComponent implements OnInit {
  readonly history = inject(HistoryFacade);

  ngOnInit(): void {
    this.history.initialize();
  }
}
