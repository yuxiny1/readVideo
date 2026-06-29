import {describe, expect, it} from "vitest";

import {ReaderHeading, ReaderLibraryItem, ReaderViewMode} from "./reader.types";

describe("reader type contracts", () => {
  it("represent headings and library rows", () => {
    const heading: ReaderHeading = {id: "section-1", level: 2, title: "Overview"};
    const item: ReaderLibraryItem = {kind: "file", path: "/notes/a.md", favorite: null, file: null};
    const mode: ReaderViewMode = "rendered";

    expect({heading, item, mode}).toEqual({
      heading: {id: "section-1", level: 2, title: "Overview"},
      item: {kind: "file", path: "/notes/a.md", favorite: null, file: null},
      mode: "rendered",
    });
  });
});
