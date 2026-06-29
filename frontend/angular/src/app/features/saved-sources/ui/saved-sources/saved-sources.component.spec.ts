import {signal} from "@angular/core";
import {TestBed} from "@angular/core/testing";
import {beforeEach, describe, expect, it, vi} from "vitest";

import {ProcessFormService} from "../../../new-video/data-access/process-form/process-form.service";
import {TaskWorkflowService} from "../../../new-video/data-access/task-workflow/task-workflow.service";
import {WatchItem} from "../../../../shared/models/readvideo-types/readvideo.types";
import {SavedSourcesComponent} from "./saved-sources.component";
import {SavedSourcesFacade} from "../../data-access/saved-sources-facade/saved-sources.facade";

const item = (id: number): WatchItem => ({
  id,
  name: `Source ${id}`,
  url: `https://example.com/${id}`,
  notes: "",
  sort_order: id,
});

describe("SavedSourcesComponent", () => {
  let component: SavedSourcesComponent;
  let sources: {
    items: ReturnType<typeof signal<WatchItem[]>>;
    orderSaving: ReturnType<typeof signal<boolean>>;
    loadWatchlist: ReturnType<typeof vi.fn>;
    persistOrder: ReturnType<typeof vi.fn>;
  };
  let form: {patch: ReturnType<typeof vi.fn>};
  let workflow: {startProcessingUrl: ReturnType<typeof vi.fn>};

  beforeEach(async () => {
    sources = {
      items: signal([item(1), item(2)]),
      orderSaving: signal(false),
      loadWatchlist: vi.fn(),
      persistOrder: vi.fn(),
    };
    form = {patch: vi.fn()};
    workflow = {startProcessingUrl: vi.fn()};
    await TestBed.configureTestingModule({
      imports: [SavedSourcesComponent],
      providers: [
        {provide: ProcessFormService, useValue: form},
        {provide: TaskWorkflowService, useValue: workflow},
      ],
    }).overrideComponent(SavedSourcesComponent, {
      set: {template: "", providers: [{provide: SavedSourcesFacade, useValue: sources}]},
    }).compileComponents();
    const fixture = TestBed.createComponent(SavedSourcesComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("loads sources and delegates URL actions", () => {
    expect(sources.loadWatchlist).toHaveBeenCalledOnce();
    component.useUrl("https://example.com/1");
    component.downloadUrl("https://example.com/2");
    expect(form.patch).toHaveBeenCalledWith({url: "https://example.com/1"});
    expect(form.patch).toHaveBeenCalledWith({url: "https://example.com/2"});
    expect(workflow.startProcessingUrl).toHaveBeenCalledWith("https://example.com/2");
  });

  it("toggles action menus", () => {
    component.toggleActions(1);
    expect(component.openActionsId()).toBe(1);
    component.toggleActions(1);
    expect(component.openActionsId()).toBeNull();
  });

  it("reorders sources through drag and drop", () => {
    const dataTransfer = {setData: vi.fn(), effectAllowed: "", dropEffect: ""};
    component.startDrag({
      target: document.createElement("div"),
      dataTransfer,
      preventDefault: vi.fn(),
    } as unknown as DragEvent, item(1));
    component.dropTarget.set({id: 2, position: "after"});
    component.dropOn({preventDefault: vi.fn()} as unknown as DragEvent, item(2));

    expect(sources.persistOrder).toHaveBeenCalledWith([item(2), item(1)], [item(1), item(2)]);
    expect(component.draggedItemId()).toBeNull();
  });

  it("formats source update metadata", () => {
    expect(component.updateMeta({title: "T", url: "u", video_id: "v", uploader: "A", upload_date: "20260601"}))
      .toBe("A / 20260601");
  });
});
