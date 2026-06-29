import {TestBed} from "@angular/core/testing";
import {beforeEach, describe, expect, it, vi} from "vitest";

import {TaskRecord} from "../../../../shared/models/readvideo-types/readvideo.types";
import {LatestOutputComponent, LatestOutputViewModel} from "./latest-output.component";

const completedTask: TaskRecord = {
  task_id: "task/1",
  status: "completed",
  summary: "Summary",
  markdown_path: "/notes/a.md",
};

describe("LatestOutputComponent", () => {
  let component: LatestOutputComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({imports: [LatestOutputComponent]})
      .overrideComponent(LatestOutputComponent, {set: {template: ""}})
      .compileComponents();
    const fixture = TestBed.createComponent(LatestOutputComponent);
    const vm: LatestOutputViewModel = {task: completedTask, summary: "Summary", recentTasks: [], canCopy: true};
    fixture.componentRef.setInput("vm", vm);
    fixture.detectChanges();
    component = fixture.componentInstance;
  });

  it("recognizes readable and favorite-ready output", () => {
    expect(component.canFavorite(completedTask)).toBe(true);
    expect(component.canRead(completedTask)).toBe(true);
    expect(component.canRead({...completedTask, status: "failed"})).toBe(false);
  });

  it("emits Reader navigation for completed Markdown", () => {
    const opened = vi.fn();
    component.readerOpened.subscribe(opened);
    component.readSummary(completedTask);
    component.readSummary(null);
    expect(opened).toHaveBeenCalledOnce();
    expect(opened).toHaveBeenCalledWith("/notes/a.md");
  });

  it("builds safe file URLs and path fallbacks", () => {
    expect(component.fileHref("markdown", completedTask)).toBe("/api/history/task%2F1/files/markdown");
    expect(component.fileHref("video", null)).toBe("");
    expect(component.taskPath(completedTask, "video_path")).toBe("-");
    expect(component.statusLabel("organizing_notes")).toBe("organizing notes");
  });
});
