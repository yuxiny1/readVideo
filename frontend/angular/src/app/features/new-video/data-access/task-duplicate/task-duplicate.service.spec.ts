import {TestBed} from "@angular/core/testing";
import {of, throwError} from "rxjs";
import {describe, expect, it, vi} from "vitest";

import {ReadvideoApiService} from "../../../../core/api/readvideo-api/readvideo-api.service";
import {TaskRecord} from "../../../../shared/models/readvideo-types/readvideo.types";
import {TaskDuplicateService} from "./task-duplicate.service";

const record: TaskRecord = {task_id: "task-1", status: "completed"};

describe("TaskDuplicateService", () => {
  it("holds reusable history only when the user must choose", () => {
    const api = {lookupHistory: vi.fn(() => of({found: true, can_reuse: true, record}))};
    TestBed.configureTestingModule({providers: [
      TaskDuplicateService,
      {provide: ReadvideoApiService, useValue: api},
    ]});
    const service = TestBed.inject(TaskDuplicateService);
    let decision = "";

    service.inspect("https://example.com").subscribe((value) => decision = value.kind);

    expect(decision).toBe("choose");
    expect(service.url()).toBe("https://example.com");
    expect(service.reusableRecord()).toEqual(record);
    service.clear();
    expect(service.lookup()).toBeNull();
  });

  it("defines lookup errors as a recoverable processing decision", () => {
    const api = {lookupHistory: vi.fn(() => throwError(() => new Error("offline")))};
    TestBed.configureTestingModule({providers: [
      TaskDuplicateService,
      {provide: ReadvideoApiService, useValue: api},
    ]});
    const service = TestBed.inject(TaskDuplicateService);

    service.inspect("https://example.com").subscribe((decision) => {
      expect(decision).toEqual({kind: "lookup-failed", message: "offline"});
    });
  });
});
