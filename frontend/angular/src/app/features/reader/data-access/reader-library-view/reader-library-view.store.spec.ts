import {signal} from "@angular/core";
import {TestBed} from "@angular/core/testing";
import {describe, expect, it} from "vitest";

import {LibraryStore} from "../../../library/data-access/library-store/library.store";
import {FavoriteSummary, MarkdownFile} from "../../../../shared/models/readvideo-types/readvideo.types";
import {ReaderLibraryViewStore} from "./reader-library-view.store";

const favorite = (overrides: Partial<FavoriteSummary> = {}): FavoriteSummary => ({
  id: 1,
  task_id: "task-1",
  folder_id: null,
  folder_name: "",
  title: "Angular Signals",
  url: "https://example.com",
  summary: "State management",
  markdown_path: "/notes/angular.md",
  notes_dir: "/notes",
  created_at: "2026-01-01",
  updated_at: "2026-01-02",
  tags: ["frontend"],
  ...overrides,
});

describe("ReaderLibraryViewStore", () => {
  it("owns filtering, counts, and file loading state", () => {
    const library = {
      favorites: signal([
        favorite(),
        favorite({id: 2, folder_id: 4, folder_name: "Work", title: "Python", tags: ["backend"]}),
      ]),
      folders: signal([{id: 4, name: "Work", notes: "", created_at: "", updated_at: ""}]),
      tags: signal([{name: "frontend", usage_count: 1}, {name: "unused", usage_count: 0}]),
    };
    TestBed.configureTestingModule({providers: [
      ReaderLibraryViewStore,
      {provide: LibraryStore, useValue: library},
    ]});
    const store = TestBed.inject(ReaderLibraryViewStore);
    const file: MarkdownFile = {name: "local.md", path: "/notes/local.md", size_bytes: 1, modified_at: ""};

    store.showFiles([file]);
    store.setActiveFolder("unfiled");
    store.setActiveTag("frontend");

    expect(store.filteredFavorites().map((item) => item.id)).toEqual([1]);
    expect(store.libraryCount()).toBe("1 篇收藏 · 1 个文件");
    expect(store.folderCount("unfiled")).toBe(1);
    expect(store.tagCount("frontend")).toBe(1);
    expect(store.visibleTags().map((tag) => tag.name)).toEqual(["frontend"]);

    store.markFilesFailed();
    expect(store.files()).toEqual([]);
    expect(store.fileCount()).toBe("加载失败");
  });

  it("normalizes invalid folder and sort selections", () => {
    const library = {favorites: signal([]), folders: signal([]), tags: signal([])};
    TestBed.configureTestingModule({providers: [
      ReaderLibraryViewStore,
      {provide: LibraryStore, useValue: library},
    ]});
    const store = TestBed.inject(ReaderLibraryViewStore);

    store.setActiveFolder("missing");
    store.setSort("missing");

    expect(store.activeFolderId()).toBe("all");
    expect(store.sort()).toBe("recent");
  });
});
