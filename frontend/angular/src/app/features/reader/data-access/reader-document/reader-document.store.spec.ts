import {TestBed} from "@angular/core/testing";
import {afterEach, beforeEach, describe, expect, it, vi} from "vitest";

import {ReaderDocumentStore} from "./reader-document.store";

describe("ReaderDocumentStore", () => {
  let store: InstanceType<typeof ReaderDocumentStore>;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({providers: [ReaderDocumentStore]});
    store = TestBed.inject(ReaderDocumentStore);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("opens Markdown and derives reader metadata", () => {
    store.open({
      path: "/notes/course.md",
      content: "# Course\nSource: https://example.com\nGenerated: today\nTranscript: `/tmp/a.txt`\n## Intro\nNote note",
    });
    store.setDocumentQuery("note");

    expect(store.status()).toBe("已打开");
    expect(store.title()).toBe("Course");
    expect(store.headings()).toHaveLength(2);
    expect(store.sourceUrl()).toBe("https://example.com");
    expect(store.transcriptPath()).toBe("/tmp/a.txt");
    expect(store.searchMatchCount()).toBe(2);
    expect(String(store.html())).toContain("Course");
  });

  it("updates reader controls and persists focus preferences", () => {
    store.toggleFocusMode();
    store.setFocusTheme("dark");
    store.setReaderWidth("wide");
    store.setReaderTextSize("large");
    store.setViewMode("markdown");

    expect(store.focusMode()).toBe(true);
    expect(store.focusTheme()).toBe("dark");
    expect(store.readerWidth()).toBe("wide");
    expect(store.readerTextSize()).toBe("large");
    expect(store.viewMode()).toBe("markdown");
    expect(localStorage.getItem("readvideo.reader.focusTheme")).toBe("dark");
  });

  it("tracks open failures without unsafe HTML", () => {
    store.beginOpen("/missing.md");
    expect(store.status()).toBe("正在加载");
    store.fail("<missing>");
    expect(store.status()).toBe("错误");
    expect(store.rawContent()).toBe("");
    expect(String(store.html())).toContain("&lt;missing&gt;");
  });

  it("copies complete Markdown and restores the open status", async () => {
    vi.useFakeTimers();
    const writeText = vi.fn(() => Promise.resolve());
    Object.defineProperty(navigator, "clipboard", {configurable: true, value: {writeText}});
    store.open({path: "/notes/a.md", content: "# Full note"});

    store.copyMarkdown();
    await vi.runAllTimersAsync();

    expect(writeText).toHaveBeenCalledWith("# Full note");
    expect(store.status()).toBe("已打开");
    expect(store.downloadHref()).toBe("/api/markdown_files/download?path=%2Fnotes%2Fa.md");
    expect(store.formatBytes(1024)).toBe("1.0 KB");
  });
});
