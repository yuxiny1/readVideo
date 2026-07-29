import {TestBed} from "@angular/core/testing";
import {describe, expect, it, vi} from "vitest";

import {TagEditorComponent} from "./tag-editor.component";

const tags = [
  {id: 1, name: "课程", task_count: 2, created_at: "2026-01-01", updated_at: "2026-01-01"},
  {id: 2, name: "AI", task_count: 1, created_at: "2026-01-01", updated_at: "2026-01-01"},
];

describe("TagEditorComponent", () => {
  it("adds suggested tags and removes selected tags", async () => {
    await TestBed.configureTestingModule({imports: [TagEditorComponent]}).compileComponents();
    const fixture = TestBed.createComponent(TagEditorComponent);
    fixture.componentRef.setInput("inputId", "tags");
    fixture.componentRef.setInput("name", "tags");
    fixture.componentRef.setInput("value", "课程");
    fixture.componentRef.setInput("suggestions", tags);
    const changed = vi.fn();
    fixture.componentInstance.valueChange.subscribe(changed);
    fixture.detectChanges();

    fixture.componentInstance.addTag("AI");
    fixture.componentInstance.removeTag("课程");

    expect(changed).toHaveBeenCalledWith("课程, AI");
    expect(changed).toHaveBeenCalledWith("");
  });

  it("emits manual input and save events", async () => {
    await TestBed.configureTestingModule({imports: [TagEditorComponent]}).compileComponents();
    const fixture = TestBed.createComponent(TagEditorComponent);
    fixture.componentRef.setInput("inputId", "tags");
    fixture.componentRef.setInput("name", "tags");
    const changed = vi.fn();
    const saved = vi.fn();
    fixture.componentInstance.valueChange.subscribe(changed);
    fixture.componentInstance.saveRequested.subscribe(saved);

    fixture.componentInstance.setValue("#商业, 课程");
    fixture.componentInstance.save();

    expect(changed).toHaveBeenCalledWith("#商业, 课程");
    expect(saved).toHaveBeenCalledOnce();
  });
});
