import {describe, expect, it} from "vitest";

import {FavoriteSummary, MarkdownFile} from "../../../../shared/models/readvideo-types/readvideo.types";
import {favoriteTitle, filterFavorites, filterFiles, libraryItems} from "./reader-library";

const favorite = (overrides: Partial<FavoriteSummary> = {}): FavoriteSummary => ({
  id: 1,
  task_id: "task-1",
  folder_id: null,
  folder_name: "",
  title: "Angular Signals",
  url: "https://example.com/video",
  summary: "A practical signals lesson",
  markdown_path: "/notes/angular.md",
  notes_dir: "/notes",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-02T00:00:00Z",
  tags: ["frontend"],
  ...overrides,
});

const file = (overrides: Partial<MarkdownFile> = {}): MarkdownFile => ({
  name: "reader.md",
  path: "/notes/reader.md",
  size_bytes: 100,
  modified_at: "2026-01-03T00:00:00Z",
  ...overrides,
});

describe("reader library selectors", () => {
  it("filters favorites by folder, tag, and query", () => {
    const items = [
      favorite(),
      favorite({id: 2, title: "Backend", folder_id: 7, folder_name: "Work", tags: ["python"]}),
    ];

    expect(filterFavorites(items, "unfiled", "frontend", "signals", "recent")).toEqual([items[0]]);
    expect(filterFavorites(items, "7", "all", "python", "recent")).toEqual([items[1]]);
  });

  it("sorts favorites without mutating the input", () => {
    const items = [favorite({id: 2, title: "Zebra"}), favorite({id: 1, title: "Alpha"})];
    const sorted = filterFavorites(items, "all", "all", "", "title");

    expect(sorted.map((item) => item.title)).toEqual(["Alpha", "Zebra"]);
    expect(items[0].title).toBe("Zebra");
  });

  it("filters and sorts Markdown files", () => {
    const files = [file(), file({name: "alpha.md", path: "/archive/alpha.md"})];
    expect(filterFiles(files, "archive", "path").map((item) => item.name)).toEqual(["alpha.md"]);
    expect(filterFiles(files, "", "title").map((item) => item.name)).toEqual(["alpha.md", "reader.md"]);
  });

  it("builds library rows for each mode", () => {
    expect(libraryItems("all", [favorite()], [file()]).map((item) => item.kind))
      .toEqual(["favorite", "file"]);
    expect(libraryItems("favorites", [favorite()], [file()])).toHaveLength(1);
    expect(libraryItems("files", [favorite()], [file()])[0].path).toBe("/notes/reader.md");
  });

  it("falls back from title to URL and task id", () => {
    expect(favoriteTitle(favorite({title: ""}))).toBe("https://example.com/video");
    expect(favoriteTitle(favorite({title: "", url: ""}))).toBe("task-1");
  });
});
