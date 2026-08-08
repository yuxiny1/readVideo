import {TestBed} from "@angular/core/testing";
import {firstValueFrom, of} from "rxjs";
import {describe, expect, it, vi} from "vitest";

import {ReadvideoApiService} from "../../../../core/api/readvideo-api/readvideo-api.service";
import {TaskOutputService} from "./task-output.service";

describe("TaskOutputService", () => {
  it("copies complete Markdown when a task has an output file", async () => {
    const api = {
      favoriteTask: vi.fn(() => of({})),
      markdownDocument: vi.fn(() => of({path: "/notes/a.md", content: "# Full note"})),
    };
    const writeText = vi.fn(() => Promise.resolve());
    Object.defineProperty(navigator, "clipboard", {configurable: true, value: {writeText}});
    TestBed.configureTestingModule({providers: [
      TaskOutputService,
      {provide: ReadvideoApiService, useValue: api},
    ]});
    const service = TestBed.inject(TaskOutputService);
    const notice = await firstValueFrom(
      service.copy({task_id: "task-1", status: "completed", markdown_path: "/notes/a.md"}),
    );

    expect(writeText).toHaveBeenCalledWith("# Full note");
    expect(notice).toBe("已复制完整 Markdown 笔记。");
  });

  it("favorites the current task without exposing API response details", () => {
    const api = {favoriteTask: vi.fn(() => of({})), markdownDocument: vi.fn()};
    TestBed.configureTestingModule({providers: [
      TaskOutputService,
      {provide: ReadvideoApiService, useValue: api},
    ]});
    const service = TestBed.inject(TaskOutputService);

    service.favorite("task-1").subscribe((notice) => expect(notice).toBe("总结已保存到收藏。"));
    expect(api.favoriteTask).toHaveBeenCalledWith("task-1");
  });
});
