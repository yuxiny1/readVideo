import {afterEach, beforeEach, describe, expect, it, vi} from "vitest";

import {
  persistFocusThemeDefault,
  persistReaderTextSizeDefault,
  persistReaderWidthDefault,
  readFocusThemeDefault,
  readReaderTextSizeDefault,
  readReaderWidthDefault,
} from "./reader-preferences";

describe("reader preferences", () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => vi.restoreAllMocks());

  it("persists and restores reader settings", () => {
    persistFocusThemeDefault("dark");
    persistReaderWidthDefault("wide");
    persistReaderTextSizeDefault("large");

    expect(readFocusThemeDefault()).toBe("dark");
    expect(readReaderWidthDefault()).toBe("wide");
    expect(readReaderTextSizeDefault()).toBe("large");
  });

  it("uses safe defaults for missing or invalid values", () => {
    localStorage.setItem("readvideo.reader.focusTheme", "sepia");
    localStorage.setItem("readvideo.reader.width", "fluid");
    localStorage.setItem("readvideo.reader.textSize", "huge");
    expect(readFocusThemeDefault()).toBe("light");
    expect(readReaderWidthDefault()).toBe("standard");
    expect(readReaderTextSizeDefault()).toBe("standard");
  });

  it("survives blocked browser storage", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });

    expect(readFocusThemeDefault()).toBe("light");
    expect(readReaderWidthDefault()).toBe("standard");
    expect(readReaderTextSizeDefault()).toBe("standard");
    expect(() => persistReaderWidthDefault("wide")).not.toThrow();
  });
});
