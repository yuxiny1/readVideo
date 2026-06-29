import {describe, expect, it} from "vitest";

import {hasTag, parseTags, tagsFor} from "./tags";

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
});
