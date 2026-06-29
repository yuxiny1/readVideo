import {afterEach, beforeEach, describe, expect, it, vi} from "vitest";

import {
  persistFocusModeDefault,
  persistFocusThemeDefault,
  persistReaderTextSizeDefault,
  persistReaderWidthDefault,
  readFocusModeDefault,
  readFocusThemeDefault,
  readReaderTextSizeDefault,
  readReaderWidthDefault,
} from "./reader-preferences";

describe("reader preferences", () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => vi.restoreAllMocks());

  it("persists and restores focus settings", () => {
    persistFocusModeDefault(true);
    persistFocusThemeDefault("dark");
    persistReaderWidthDefault("wide");
    persistReaderTextSizeDefault("large");

    expect(readFocusModeDefault()).toBe(true);
    expect(readFocusThemeDefault()).toBe("dark");
    expect(readReaderWidthDefault()).toBe("wide");
    expect(readReaderTextSizeDefault()).toBe("large");
  });

  it("uses safe defaults for missing or invalid values", () => {
    localStorage.setItem("readvideo.reader.focusMode", "yes");
    localStorage.setItem("readvideo.reader.focusTheme", "sepia");
    localStorage.setItem("readvideo.reader.width", "fluid");
    localStorage.setItem("readvideo.reader.textSize", "huge");
    expect(readFocusModeDefault()).toBe(false);
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

    expect(readFocusModeDefault()).toBe(false);
    expect(readFocusThemeDefault()).toBe("light");
    expect(readReaderWidthDefault()).toBe("standard");
    expect(readReaderTextSizeDefault()).toBe("standard");
    expect(() => persistFocusModeDefault(true)).not.toThrow();
    expect(() => persistReaderWidthDefault("wide")).not.toThrow();
  });
});
