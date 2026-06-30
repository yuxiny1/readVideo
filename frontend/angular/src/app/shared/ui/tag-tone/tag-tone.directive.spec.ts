import {Component, signal} from "@angular/core";
import {TestBed} from "@angular/core/testing";
import {describe, expect, it} from "vitest";

import {tagToneClass} from "../../utils/tags/tags";
import {TagToneDirective} from "./tag-tone.directive";

@Component({
  standalone: true,
  imports: [TagToneDirective],
  template: '<span class="tag-chip" [rvTagTone]="tag()">#{{ tag() }}</span>',
})
class TagToneHostComponent {
  readonly tag = signal("Angular");
}

describe("TagToneDirective", () => {
  it("adds and updates the deterministic tone without removing static classes", async () => {
    await TestBed.configureTestingModule({imports: [TagToneHostComponent]}).compileComponents();
    const fixture = TestBed.createComponent(TagToneHostComponent);
    fixture.detectChanges();
    const element = fixture.nativeElement.querySelector("span") as HTMLElement;

    expect(element.classList).toContain("tag-chip");
    expect(element.classList).toContain(tagToneClass("Angular"));

    const initialTone = tagToneClass("Angular");
    const nextTag = ["Reader", "金融", "跑步"].find((tag) => tagToneClass(tag) !== initialTone) ?? "Reader";
    fixture.componentInstance.tag.set(nextTag);
    await fixture.whenStable();

    expect(element.classList).not.toContain(initialTone);
    expect(element.classList).toContain(tagToneClass(nextTag));
  });
});
