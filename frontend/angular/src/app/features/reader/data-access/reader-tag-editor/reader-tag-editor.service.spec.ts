import {signal} from "@angular/core";
import {TestBed} from "@angular/core/testing";
import {of} from "rxjs";
import {describe, expect, it, vi} from "vitest";

import {LibraryStore} from "../../../library/data-access/library-store/library.store";
import {FavoriteSummary} from "../../../../shared/models/readvideo-types/readvideo.types";
import {ReaderDocumentStore} from "../reader-document/reader-document.store";
import {ReaderHistoryContextService} from "../reader-history-context/reader-history-context.service";
import {ReaderTagEditorService} from "./reader-tag-editor.service";

const favorite: FavoriteSummary = {
  id: 1,
  task_id: "task-1",
  folder_id: null,
  folder_name: "",
  title: "Note",
  url: "https://example.com",
  summary: "Summary",
  markdown_path: "/notes/note.md",
  notes_dir: "/notes",
  created_at: "",
  updated_at: "",
  tags: ["reader"],
};

describe("ReaderTagEditorService", () => {
  it("selects the persistence target and saves favorite tags", () => {
    const updateTags = vi.fn();
    const history = {
      activeTask: signal(null),
      clear: vi.fn(),
      load: vi.fn(() => of({})),
      activeDraft: vi.fn(() => ""),
      setActiveDraft: vi.fn(),
      saveActiveTags: vi.fn(() => of({})),
    };
    const document = {
      path: signal("/mounted/notes/note.md"),
      status: signal("已打开"),
      setStatus: vi.fn(),
    };
    const library = {
      favorites: signal([favorite]),
      notice: signal(""),
      error: signal(""),
      updateTags,
      loadAll: vi.fn(),
    };
    TestBed.configureTestingModule({providers: [
      ReaderTagEditorService,
      {provide: LibraryStore, useValue: library},
      {provide: ReaderDocumentStore, useValue: document},
      {provide: ReaderHistoryContextService, useValue: history},
    ]});
    const editor = TestBed.inject(ReaderTagEditorService);

    expect(editor.selectPath("/mounted/notes/note.md")).toEqual(favorite);
    expect(editor.activeTags()).toEqual(["reader"]);
    editor.setActiveDraft("#Angular, notes");
    editor.saveActiveTags();

    expect(updateTags).toHaveBeenCalledWith({favoriteId: 1, tags: ["Angular", "notes"]});
    expect(document.setStatus).toHaveBeenCalledWith("正在保存标签");
  });
});
