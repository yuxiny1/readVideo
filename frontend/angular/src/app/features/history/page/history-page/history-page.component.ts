import {CommonModule} from "@angular/common";
import {ChangeDetectionStrategy, Component, inject, OnInit} from "@angular/core";
import {FormsModule} from "@angular/forms";

import {TagChipComponent} from "../../../../shared/ui/tag-chip/tag-chip.component";
import {HistoryFacade} from "../../data-access/history-facade/history.facade";

@Component({
  selector: "rv-history-page",
  standalone: true,
  imports: [CommonModule, FormsModule, TagChipComponent],
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
