import {CommonModule} from "@angular/common";
import {ChangeDetectionStrategy, Component, computed, input, output} from "@angular/core";
import {FormsModule} from "@angular/forms";

import {TagSummary} from "../../models/readvideo-types/readvideo.types";
import {hasTag, parseTags} from "../../utils/tags/tags";
import {TagChipComponent} from "../tag-chip/tag-chip.component";

@Component({
  selector: "rv-tag-editor",
  standalone: true,
  imports: [CommonModule, FormsModule, TagChipComponent],
  templateUrl: "./tag-editor.component.html",
  styleUrl: "./tag-editor.component.scss",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TagEditorComponent {
  readonly inputId = input.required<string>();
  readonly name = input.required<string>();
  readonly value = input("");
  readonly suggestions = input<readonly TagSummary[]>([]);
  readonly disabled = input(false);
  readonly placeholder = input("选择已有标签，或输入新标签");
  readonly saveLabel = input("保存标签");
  readonly valueChange = output<string>();
  readonly saveRequested = output<void>();

  readonly selectedTags = computed(() => parseTags(this.value()));
  readonly suggestedTags = computed(() => this.suggestions()
    .filter((tag) => !hasTag(this.selectedTags(), tag.name))
    .slice(0, 10));

  setValue(value: string): void {
    this.valueChange.emit(value);
  }

  addTag(tag: string): void {
    if (this.disabled()) return;
    const next = [...this.selectedTags(), tag];
    this.valueChange.emit(parseTags(next.join(", ")).join(", "));
  }

  removeTag(tag: string): void {
    if (this.disabled()) return;
    this.valueChange.emit(this.selectedTags().filter((item) => !hasTag([item], tag)).join(", "));
  }

  save(): void {
    if (!this.disabled()) this.saveRequested.emit();
  }

  datalistId(): string {
    return `${this.inputId()}-suggestions`;
  }
}
