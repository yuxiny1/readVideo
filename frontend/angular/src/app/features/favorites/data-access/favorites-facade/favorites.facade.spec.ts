import {TestBed} from "@angular/core/testing";
import {Router} from "@angular/router";
import {of} from "rxjs";
import {beforeEach, describe, expect, it, vi} from "vitest";

import {ReadvideoApiService} from "../../../../core/api/readvideo-api/readvideo-api.service";
import {LibraryStore} from "../../../library/data-access/library-store/library.store";
import {FavoriteFolder, FavoriteSummary} from "../../../../shared/models/readvideo-types/readvideo.types";
import {FavoritesFacade} from "./favorites.facade";

const favorite = (overrides: Partial<FavoriteSummary> = {}): FavoriteSummary => ({
  id: 1,
  task_id: "task-1",
  folder_id: null,
  folder_name: "",
  title: "Angular Reader",
  url: "https://example.com",
  summary: "Signals",
  markdown_path: "/notes/a.md",
  notes_dir: "/notes",
  created_at: "2026-01-01",
  updated_at: "2026-01-01",
  tags: ["frontend"],
  ...overrides,
});

const folder: FavoriteFolder = {
  id: 4,
  name: "Courses",
  notes: "Learning",
  created_at: "2026-01-01",
  updated_at: "2026-01-01",
};

describe("FavoritesFacade", () => {
  let facade: FavoritesFacade;
  let api: Record<string, ReturnType<typeof vi.fn>>;
  let router: {navigate: ReturnType<typeof vi.fn>};

  beforeEach(() => {
    api = {
      favorites: vi.fn(() => of([favorite(), favorite({id: 2, folder_id: 4, folder_name: "Courses", tags: ["work"]})])),
      favoriteFolders: vi.fn(() => of([folder])),
      tags: vi.fn(() => of([{
        id: 1,
        name: "frontend",
        task_count: 99,
        created_at: "2026-01-01",
        updated_at: "2026-01-01",
      }])),
      addFavoriteFolder: vi.fn(() => of(folder)),
      updateFavoriteFolder: vi.fn(() => of(folder)),
      assignFavoriteFolder: vi.fn(() => of(favorite({folder_id: 4}))),
      deleteFavorite: vi.fn(() => of({})),
      updateFavoriteTags: vi.fn(() => of(favorite({tags: ["updated"]}))),
      favoriteMarkdown: vi.fn(() => of({path: "/generated.md", content: "# Note"})),
    };
    router = {navigate: vi.fn(() => Promise.resolve(true))};
    TestBed.configureTestingModule({providers: [
      LibraryStore,
      FavoritesFacade,
      {provide: ReadvideoApiService, useValue: api},
      {provide: Router, useValue: router},
    ]});
    facade = TestBed.inject(FavoritesFacade);
    facade.initialize();
  });

  it("filters favorites by folder, tag, and text", () => {
    facade.setActiveFolder("unfiled");
    facade.setActiveTag("frontend");
    facade.setSearchQuery("signals");
    expect(facade.filteredFavorites().map((item) => item.id)).toEqual([1]);
    expect(facade.favoritesCount()).toBe("显示 1 篇，共收藏 2 篇");
    expect(facade.tagCount("frontend")).toBe(1);
    expect(facade.visibleTags()).toHaveLength(1);
  });

  it("delegates folder and tag commands to the library store", () => {
    facade.folderName = " New Folder ";
    facade.folderNotes = " Notes ";
    facade.createFolder();
    expect(api.addFavoriteFolder).toHaveBeenCalledWith("New Folder", "Notes");

    const value = facade.favorites()[0];
    facade.setTagDraft(value, "#Angular, Reader");
    facade.saveTags(value);
    expect(api.updateFavoriteTags).toHaveBeenCalledWith(1, ["Angular", "Reader"]);
  });

  it("edits folder drafts and exposes folder metadata", () => {
    facade.beginEditFolder(folder);
    facade.setFolderDraftName(folder, "Updated");
    facade.setFolderDraftNotes(folder, "Text");
    facade.saveFolder(folder);
    expect(api.updateFavoriteFolder).toHaveBeenCalledWith(4, "Updated", "Text");
    expect(facade.folderInitial(folder)).toBe("C");
    expect(facade.folderTags("4")).toEqual(["work"]);
  });

  it("opens Markdown and folder selections in Reader", () => {
    facade.readFavorite(facade.favorites()[0]);
    facade.openFolderInReader(4);
    expect(router.navigate).toHaveBeenCalledWith(["/reader"], {queryParams: {path: "/notes/a.md"}});
    expect(router.navigate).toHaveBeenCalledWith(["/reader"], {queryParams: {favoriteFolderId: "4"}});
  });
});
