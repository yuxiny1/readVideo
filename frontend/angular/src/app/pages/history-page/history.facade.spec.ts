import {TestBed} from "@angular/core/testing";
import {of, throwError} from "rxjs";
import {beforeEach, describe, expect, it, vi} from "vitest";

import {ReadvideoApiService} from "../../services/readvideo-api.service";
import {TagSummary, TaskRecord} from "../../types/readvideo.types";
import {HistoryFacade} from "./history.facade";

const record = (overrides: Partial<TaskRecord> = {}): TaskRecord => ({
  task_id: "task-1",
  status: "completed",
  title: "Angular Course",
  summary: "Signals and stores",
  markdown_path: "/notes/angular.md",
  tags: ["frontend"],
  ...overrides,
});

const tag: TagSummary = {
  id: 1,
  name: "frontend",
  task_count: 1,
  created_at: "2026-01-01",
  updated_at: "2026-01-01",
};

describe("HistoryFacade", () => {
  let facade: HistoryFacade;
  let api: Record<string, ReturnType<typeof vi.fn>>;

  beforeEach(() => {
    api = {
      history: vi.fn(() => of([record(), record({task_id: "task-2", title: "Python", tags: ["backend"]})])),
      tags: vi.fn(() => of([tag])),
      favoriteTask: vi.fn(() => of({})),
      updateHistoryTags: vi.fn((taskId: string, tags: string[]) => of(record({task_id: taskId, tags}))),
    };
    TestBed.configureTestingModule({providers: [
      HistoryFacade,
      {provide: ReadvideoApiService, useValue: api},
    ]});
    facade = TestBed.inject(HistoryFacade);
  });

  it("loads history and filters by tag and query", () => {
    facade.initialize();
    expect(facade.records()).toHaveLength(2);
    expect(facade.visibleCountLabel()).toBe("2 shown / 2 records");

    facade.setActiveTag("frontend");
    facade.searchQuery.set("signals");
    expect(facade.filteredRecords().map((value) => value.task_id)).toEqual(["task-1"]);
    expect(facade.tagCount("backend")).toBe(1);
  });

  it("favorites a record and refreshes history", () => {
    facade.favorite(record());
    expect(api.favoriteTask).toHaveBeenCalledWith("task-1");
    expect(facade.notice()).toBe("Favorite saved");
  });

  it("normalizes and saves record tags", () => {
    const value = record();
    facade.initialize();
    facade.setTagDraft(value, "#Angular, notes");
    facade.saveTags(value);

    expect(api.updateHistoryTags).toHaveBeenCalledWith("task-1", ["Angular", "notes"]);
    expect(facade.records()[0].tags).toEqual(["Angular", "notes"]);
    expect(facade.notice()).toBe("Tags saved");
  });

  it("exposes load failures", () => {
    api.history.mockReturnValue(throwError(() => new Error("history failed")));
    facade.initialize();
    expect(facade.countLabel()).toBe("Error");
    expect(facade.error()).toBe("history failed");
  });
});
