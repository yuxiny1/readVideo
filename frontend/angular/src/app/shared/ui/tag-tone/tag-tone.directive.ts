import {Directive, ElementRef, Input, Renderer2, inject} from "@angular/core";

import {TagToneClass, tagToneClass} from "../../utils/tags/tags";

@Directive({
  selector: "[rvTagTone]",
  standalone: true,
})
export class TagToneDirective {
  private readonly element = inject<ElementRef<HTMLElement>>(ElementRef);
  private readonly renderer = inject(Renderer2);
  private currentTone: TagToneClass | null = null;

  @Input({required: true})
  set rvTagTone(tag: string) {
    if (this.currentTone) this.renderer.removeClass(this.element.nativeElement, this.currentTone);
    this.currentTone = tagToneClass(tag);
    this.renderer.addClass(this.element.nativeElement, this.currentTone);
  }
}
