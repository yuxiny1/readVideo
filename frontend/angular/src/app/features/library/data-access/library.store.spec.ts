import {TestBed} from "@angular/core/testing";
import {of, throwError} from "rxjs";
import {beforeEach, describe, expect, it, vi} from "vitest";

import {FavoriteFolder, FavoriteSummary, TagSummary} from "../../../types/readvideo.types";
import {ReadvideoApiService} from "../../../services/readvideo-api.service";
import {LibraryStore} from "./library.store";

const favorite = (overrides: Partial<FavoriteSummary> = {}): FavoriteSummary => ({
  id: 1,
  task_id: "task-1",
  folder_id: null,
  folder_name: "",
  title: "Reader",
  url: "https://example.com",
  summary: "Summary",
  markdown_path: "/notes/reader.md",
  notes_dir: "/notes",
  created_at: "2026-01-01",
  updated_at: "2026-01-01",
  tags: [],
  ...overrides,
});

const folder = (overrides: Partial<FavoriteFolder> = {}): FavoriteFolder => ({
  id: 4,
  name: "Courses",
  notes: "",
  created_at: "2026-01-01",
  updated_at: "2026-01-01",
  ...overrides,
});

const tag = (name: string): TagSummary => ({
  id: 1,
  name,
  task_count: 1,
  created_at: "2026-01-01",
  updated_at: "2026-01-01",
});

describe("LibraryStore", () => {
  let store: InstanceType<typeof LibraryStore>;
  let api: Record<string, ReturnType<typeof vi.fn>>;

  beforeEach(() => {
    api = {
      favorites: vi.fn(() => of([favorite()])),
      favoriteFolders: vi.fn(() => of([folder()])),
      tags: vi.fn(() => of([tag("reader")])),
      addFavoriteFolder: vi.fn(() => of(folder({id: 5, name: "New"}))),
      updateFavoriteFolder: vi.fn(() => of(folder({name: "Updated"}))),
      assignFavoriteFolder: vi.fn(() => of(favorite({folder_id: 4, folder_name: "Courses"}))),
      deleteFavorite: vi.fn(() => of({})),
      updateFavoriteTags: vi.fn(() => of(favorite({tags: ["angular"]}))),
    };
    TestBed.configureTestingModule({providers: [
      LibraryStore,
      {provide: ReadvideoApiService, useValue: api},
    ]});
    store = TestBed.inject(LibraryStore);
  });

  it("loads favorites, folders, and tags into derived state", () => {
    store.loadAll();
    expect(store.favorites()).toHaveLength(1);
    expect(store.favoriteCount()).toBe(1);
    expect(store.folderCount()).toBe(1);
    expect(store.tagCount()).toBe(1);
    expect(store.loading()).toBe(false);
  });

  it("creates and updates folders", () => {
    store.loadAll();
    store.createFolder({name: "New", notes: "N"});
    expect(api.addFavoriteFolder).toHaveBeenCalledWith("New", "N");
    expect(store.notice()).toBe("Folder created");

    api.favorites.mockReturnValue(of([favorite({folder_name: "Updated"})]));
    store.updateFolder({folderId: 4, name: "Updated", notes: "Text"});
    expect(store.folders()[0].name).toBe("Updated");
    expect(store.notice()).toBe("Folder updated");
  });

  it("assigns folders and updates tags immutably", () => {
    store.loadAll();
    const original = store.favorites();
    store.assignFolder({favoriteId: 1, folderId: 4});
    expect(store.favorites()[0].folder_id).toBe(4);
    expect(store.favorites()).not.toBe(original);

    api.tags.mockReturnValue(of([tag("angular")]));
    store.updateTags({favoriteId: 1, tags: ["angular"]});
    expect(store.favorites()[0].tags).toEqual(["angular"]);
    expect(store.tags()[0].name).toBe("angular");
    expect(store.notice()).toBe("Tags saved");
  });

  it("refreshes collections after deletion", () => {
    store.loadAll();
    api.favorites.mockReturnValue(of([]));
    api.favoriteFolders.mockReturnValue(of([]));
    api.tags.mockReturnValue(of([]));
    store.deleteFavorite(1);

    expect(api.deleteFavorite).toHaveBeenCalledWith(1);
    expect(store.favorites()).toEqual([]);
    expect(store.notice()).toBe("Favorite removed");
  });

  it("captures request errors and always clears loading", () => {
    api.favorites.mockReturnValue(throwError(() => new Error("database unavailable")));
    store.loadAll();
    expect(store.error()).toBe("database unavailable");
    expect(store.loading()).toBe(false);

    store.clearFeedback();
    expect(store.error()).toBe("");
  });
});
