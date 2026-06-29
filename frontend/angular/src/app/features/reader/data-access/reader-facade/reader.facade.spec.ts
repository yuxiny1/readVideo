import {TestBed} from "@angular/core/testing";
import {ActivatedRoute, Router, convertToParamMap} from "@angular/router";
import {Subject, of, throwError} from "rxjs";
import {beforeEach, describe, expect, it, vi} from "vitest";

import {ReadvideoApiService} from "../../../../core/api/readvideo-api/readvideo-api.service";
import {LibraryStore} from "../../../library/data-access/library-store/library.store";
import {FavoriteFolder, FavoriteSummary, MarkdownFile} from "../../../../shared/models/readvideo-types/readvideo.types";
import {ReaderDocumentStore} from "../reader-document/reader-document.store";
import {ReaderFacade} from "./reader.facade";

const favorite = (overrides: Partial<FavoriteSummary> = {}): FavoriteSummary => ({
  id: 1,
  task_id: "task-1",
  folder_id: null,
  folder_name: "",
  title: "Reader Note",
  url: "https://example.com",
  summary: "Summary",
  markdown_path: "/notes/a.md",
  notes_dir: "/notes",
  created_at: "2026-01-01",
  updated_at: "2026-01-01",
  tags: ["reader"],
  ...overrides,
});

const folder: FavoriteFolder = {
  id: 4,
  name: "Courses",
  notes: "",
  created_at: "2026-01-01",
  updated_at: "2026-01-01",
};

const file: MarkdownFile = {
  name: "a.md",
  path: "/notes/a.md",
  size_bytes: 100,
  modified_at: "2026-01-02",
};

describe("ReaderFacade", () => {
  let facade: ReaderFacade;
  let documentStore: InstanceType<typeof ReaderDocumentStore>;
  let api: Record<string, ReturnType<typeof vi.fn>>;
  let router: {navigate: ReturnType<typeof vi.fn>};

  beforeEach(() => {
    localStorage.clear();
    api = {
      favorites: vi.fn(() => of([
        favorite(),
        favorite({id: 2, markdown_path: "/notes/b.md", folder_id: 4, tags: ["work"]}),
      ])),
      favoriteFolders: vi.fn(() => of([folder])),
      tags: vi.fn(() => of([])),
      updateFavoriteTags: vi.fn((_id: number, tags: string[]) => of(favorite({tags}))),
      appConfig: vi.fn(() => of({notes_dir: "/notes"})),
      markdownFiles: vi.fn(() => of([file])),
      markdownDocument: vi.fn((path: string) => of({path, content: "# Reader Note\nBody"})),
      favoriteMarkdown: vi.fn(() => of({path: "/notes/generated.md", content: "# Generated"})),
    };
    router = {navigate: vi.fn(() => Promise.resolve(true))};
    TestBed.configureTestingModule({providers: [
      LibraryStore,
      ReaderDocumentStore,
      ReaderFacade,
      {provide: ReadvideoApiService, useValue: api},
      {provide: Router, useValue: router},
      {provide: ActivatedRoute, useValue: {
        snapshot: {queryParamMap: convertToParamMap({folder: "/notes", path: "/notes/a.md"})},
      }},
    ]});
    facade = TestBed.inject(ReaderFacade);
    documentStore = TestBed.inject(ReaderDocumentStore);
  });

  it("initializes library data and opens the routed document", () => {
    facade.initialize();
    TestBed.tick();

    expect(facade.defaultNotesDir()).toBe("/notes");
    expect(facade.files()).toEqual([file]);
    expect(documentStore.path()).toBe("/notes/a.md");
    expect(documentStore.title()).toBe("Reader Note");
    expect(facade.libraryCount()).toBe("2 篇收藏 · 1 个文件");
  });

  it("filters, sorts, and navigates adjacent library documents", () => {
    facade.initialize();
    TestBed.tick();
    facade.setLibraryMode("favorites");
    facade.setLibrarySort("title");
    facade.setActiveTag("reader");

    expect(facade.visibleLibraryItems()).toHaveLength(1);
    expect(facade.isActivePath("/notes/a.md")).toBe(true);
    expect(facade.canOpenNext()).toBe(false);
    expect(facade.tagCount("reader")).toBe(1);
  });

  it("saves tags for the active favorite", () => {
    facade.initialize();
    TestBed.tick();
    facade.setActiveTagDraft("#Angular, notes");
    facade.saveActiveTags();
    TestBed.tick();

    expect(api.updateFavoriteTags).toHaveBeenCalledWith(1, ["Angular", "notes"]);
    expect(documentStore.status()).toBe("标签已保存");
  });

  it("keeps the Reader usable when file loading fails", () => {
    api.markdownFiles.mockReturnValue(throwError(() => new Error("folder unavailable")));
    facade.loadMarkdownFiles("/missing");
    expect(facade.fileCount()).toBe("加载失败");
    expect(facade.files()).toEqual([]);
    expect(facade.error()).toBe("folder unavailable");
  });

  it("keeps the newest document when older requests finish later", () => {
    const first = new Subject<{path: string; content: string}>();
    const second = new Subject<{path: string; content: string}>();
    api.markdownDocument.mockImplementation((path: string) => path.endsWith("first.md") ? first : second);

    facade.openPath("/notes/first.md");
    facade.openPath("/notes/second.md");
    second.next({path: "/notes/second.md", content: "# 第二篇"});
    first.next({path: "/notes/first.md", content: "# 第一篇"});

    expect(documentStore.path()).toBe("/notes/second.md");
    expect(documentStore.title()).toBe("第二篇");
  });
});
