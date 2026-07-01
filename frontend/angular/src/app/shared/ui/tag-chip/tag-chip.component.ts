import {NgClass} from "@angular/common";
import {ChangeDetectionStrategy, Component, computed, input, output} from "@angular/core";

import {tagToneClass} from "../../utils/tags/tags";

@Component({
  selector: "rv-tag-chip",
  standalone: true,
  imports: [NgClass],
  templateUrl: "./tag-chip.component.html",
  styleUrl: "./tag-chip.component.scss",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TagChipComponent {
  readonly label = input.required<string>();
  readonly count = input<number | null>(null);
  readonly active = input(false);
  readonly muted = input(false);
  readonly mini = input(false);
  readonly colored = input(true);
  readonly interactive = input(true);
  readonly prefix = input(true);
  readonly selected = output<void>();
  readonly toneClass = computed(() => this.colored() ? tagToneClass(this.label()) : "");
}
