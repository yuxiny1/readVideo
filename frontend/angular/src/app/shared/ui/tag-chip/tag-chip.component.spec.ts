import {TestBed} from "@angular/core/testing";
import {describe, expect, it, vi} from "vitest";

import {tagToneClass} from "../../utils/tags/tags";
import {TagChipComponent} from "./tag-chip.component";

describe("TagChipComponent", () => {
  it("renders a stable colored interactive tag", async () => {
    await TestBed.configureTestingModule({imports: [TagChipComponent]}).compileComponents();
    const fixture = TestBed.createComponent(TagChipComponent);
    fixture.componentRef.setInput("label", "Angular");
    fixture.componentRef.setInput("count", 3);
    fixture.componentRef.setInput("active", true);
    fixture.detectChanges();
    const button = fixture.nativeElement.querySelector("button") as HTMLButtonElement;

    expect(button.textContent).toContain("#Angular");
    expect(button.textContent).toContain("3");
    expect(button.classList).toContain(tagToneClass("Angular"));
    expect(button.classList).toContain("active");
  });

  it("emits selection and supports neutral non-interactive labels", async () => {
    await TestBed.configureTestingModule({imports: [TagChipComponent]}).compileComponents();
    const fixture = TestBed.createComponent(TagChipComponent);
    const selected = vi.fn();
    fixture.componentInstance.selected.subscribe(selected);
    fixture.componentRef.setInput("label", "全部");
    fixture.componentRef.setInput("colored", false);
    fixture.componentRef.setInput("prefix", false);
    fixture.detectChanges();
    (fixture.nativeElement.querySelector("button") as HTMLButtonElement).click();
    expect(selected).toHaveBeenCalledOnce();

    fixture.componentRef.setInput("interactive", false);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector("span.tag-chip")).not.toBeNull();
  });
});
