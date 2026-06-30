import {describe, expect, it} from "vitest";

import {hasTag, parseTags, tagsFor, tagToneClass} from "./tags";

describe("tag helpers", () => {
  it("reads tags without manufacturing state", () => {
    expect(tagsFor({tags: ["Angular"]})).toEqual(["Angular"]);
    expect(tagsFor({})).toEqual([]);
  });

  it("matches tags case-insensitively", () => {
    expect(hasTag(["Angular", "Reader"], "angular")).toBe(true);
    expect(hasTag(["Angular"], "RxJS")).toBe(false);
  });

  it("parses comma, semicolon, newline, and hashtag input", () => {
    expect(parseTags("#Angular, RxJS; notes\nAngular"))
      .toEqual(["Angular", "RxJS", "notes"]);
    expect(parseTags("   ")).toEqual([]);
  });

  it("assigns stable but varied color tones from tag names", () => {
    expect(tagToneClass("Angular")).toBe(tagToneClass("angular"));
    const tones = new Set([
      "人工智能", "金融", "跑步", "课程", "英国", "食谱", "工作", "技术",
    ].map(tagToneClass));
    expect(tones.size).toBeGreaterThanOrEqual(4);
  });
});
