import {signal} from "@angular/core";
import {TestBed} from "@angular/core/testing";
import {of, throwError} from "rxjs";
import {beforeEach, describe, expect, it, vi} from "vitest";

import {ReadvideoApiService} from "../../services/readvideo-api.service";
import {TaskWorkflowService} from "../../services/task-workflow.service";
import {WatchItem} from "../../types/readvideo.types";
import {SavedSourcesFacade} from "./saved-sources.facade";

const item = (id: number, name = `Source ${id}`): WatchItem => ({
  id,
  name,
  url: `https://example.com/${id}`,
  notes: "",
  sort_order: id,
});

describe("SavedSourcesFacade", () => {
  let facade: SavedSourcesFacade;
  let api: Record<string, ReturnType<typeof vi.fn>>;
  let workflow: {notice: ReturnType<typeof signal<{text: string; kind: "muted" | "error"}>>};

  beforeEach(() => {
    api = {
      watchlist: vi.fn(() => of([item(1), item(2)])),
      addWatchItem: vi.fn(() => of(item(3))),
      sourceUpdates: vi.fn(() => of({source: item(1), updates: [{title: "New", url: "u", video_id: "v"}]})),
      deleteWatchItem: vi.fn(() => of({})),
      reorderWatchItems: vi.fn((ids: number[]) => of(ids.map((id) => item(id)))),
    };
    workflow = {notice: signal({text: "Idle", kind: "muted" as const})};
    TestBed.configureTestingModule({providers: [
      SavedSourcesFacade,
      {provide: ReadvideoApiService, useValue: api},
      {provide: TaskWorkflowService, useValue: workflow},
    ]});
    facade = TestBed.inject(SavedSourcesFacade);
  });

  it("loads, adds, and deletes saved sources", () => {
    facade.loadWatchlist();
    expect(facade.items().map((value) => value.id)).toEqual([1, 2]);

    facade.newItem = {name: " New ", url: " https://new.test ", notes: " note "};
    facade.addWatchItem();
    expect(api.addWatchItem).toHaveBeenCalledWith({name: "New", url: "https://new.test", notes: "note"});
    expect(facade.newItem).toEqual({name: "", url: "", notes: ""});

    facade.deleteItem(item(1));
    expect(api.deleteWatchItem).toHaveBeenCalledWith(1);
  });

  it("loads per-source updates", () => {
    facade.loadUpdates(item(1));
    expect(facade.updates()["1"][0].title).toBe("New");
    expect(facade.errors()["1"]).toBe("");
  });

  it("persists manual order", () => {
    facade.persistOrder([item(2), item(1)], [item(1), item(2)]);
    expect(api.reorderWatchItems).toHaveBeenCalledWith([2, 1]);
    expect(facade.items().map((value) => value.id)).toEqual([2, 1]);
    expect(facade.orderSaving()).toBe(false);
  });

  it("rolls back order and reports an API failure", () => {
    api.reorderWatchItems.mockReturnValue(throwError(() => new Error("save failed")));
    facade.persistOrder([item(2), item(1)], [item(1), item(2)]);

    expect(facade.items().map((value) => value.id)).toEqual([1, 2]);
    expect(workflow.notice()).toEqual({text: "save failed", kind: "error"});
  });
});
