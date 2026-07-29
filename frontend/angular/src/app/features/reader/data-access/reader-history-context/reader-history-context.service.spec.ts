import {TestBed} from "@angular/core/testing";
import {of} from "rxjs";
import {beforeEach, describe, expect, it, vi} from "vitest";

import {ReadvideoApiService} from "../../../../core/api/readvideo-api/readvideo-api.service";
import {TaskRecord} from "../../../../shared/models/readvideo-types/readvideo.types";
import {ReaderHistoryContextService} from "./reader-history-context.service";

const task = (overrides: Partial<TaskRecord> = {}): TaskRecord => ({
  task_id: "task-1",
  status: "completed",
  markdown_path: "/notes/a.md",
  tags: ["课程"],
  ...overrides,
});

describe("ReaderHistoryContextService", () => {
  let service: ReaderHistoryContextService;
  let api: Record<string, ReturnType<typeof vi.fn>>;

  beforeEach(() => {
    api = {
      taskStatus: vi.fn((taskId: string) => of(task({task_id: taskId}))),
      updateHistoryTags: vi.fn((taskId: string, tags: string[]) => of(task({task_id: taskId, tags}))),
    };
    TestBed.configureTestingModule({providers: [
      ReaderHistoryContextService,
      {provide: ReadvideoApiService, useValue: api},
    ]});
    service = TestBed.inject(ReaderHistoryContextService);
  });

  it("loads a task and keeps a tag draft", () => {
    service.load("history-task").subscribe();

    expect(api.taskStatus).toHaveBeenCalledWith("history-task");
    expect(service.activeTask()?.task_id).toBe("history-task");
    expect(service.activeDraft()).toBe("课程");
  });

  it("saves edited tags back to history", () => {
    service.load("history-task").subscribe();
    service.setActiveDraft("#reader, 课程");
    service.saveActiveTags().subscribe();

    expect(api.updateHistoryTags).toHaveBeenCalledWith("history-task", ["reader", "课程"]);
    expect(service.activeTask()?.tags).toEqual(["reader", "课程"]);
  });
});
