import {describe, expect, it} from "vitest";

import {
  countMatches,
  escapeHtml,
  extractHeadings,
  extractMetadata,
  extractTitle,
  fileName,
  readingStats,
  renderMarkdown,
} from "./reader-markdown";

describe("reader Markdown helpers", () => {
  it("extracts metadata, title, and supported headings", () => {
    const markdown = "# Main title\nSource: https://example.com\n## **Section**\n#### Hidden";
    expect(extractTitle(markdown)).toBe("Main title");
    expect(extractMetadata(markdown, "Source")).toBe("https://example.com");
    expect(extractMetadata(markdown, "Transcript")).toBe("");
    expect(extractHeadings(markdown)).toEqual([
      {id: "section-1", level: 1, title: "Main title"},
      {id: "section-2", level: 2, title: "Section"},
    ]);
  });

  it("counts non-overlapping case-insensitive matches", () => {
    expect(countMatches("Note note notebook", "note")).toBe(3);
    expect(countMatches("content", " ")).toBe(0);
  });

  it("formats cross-platform file names and reading time", () => {
    expect(fileName("C:\\notes\\summary.md")).toBe("summary.md");
    expect(fileName("")).toBe("Markdown note");
    expect(readingStats("short note")).toBe("1 min read");
  });

  it("renders headings, emphasis, lists, quotes, rules, and code safely", () => {
    const html = renderMarkdown([
      "# **Title**",
      "",
      "- first",
      "- `second`",
      "1. numbered",
      "> quote",
      "---",
      "```",
      "<script>alert(1)</script>",
      "```",
      "plain *text*",
    ].join("\n"));

    expect(html).toContain('<h1 id="section-1"><strong>Title</strong></h1>');
    expect(html).toContain("<ul><li>first</li><li><code>second</code></li></ul>");
    expect(html).toContain("<ol><li>numbered</li></ol>");
    expect(html).toContain("<blockquote>quote</blockquote><hr>");
    expect(html).toContain("&lt;script&gt;alert(1)&lt;/script&gt;");
    expect(html).toContain("<p>plain <em>text</em></p>");
  });

  it("escapes HTML special characters", () => {
    expect(escapeHtml(`<a title="x">Tom & 'Sam'</a>`))
      .toBe("&lt;a title=&quot;x&quot;&gt;Tom &amp; &#39;Sam&#39;&lt;/a&gt;");
  });
});
