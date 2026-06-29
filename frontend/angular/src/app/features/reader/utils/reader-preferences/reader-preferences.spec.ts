import {afterEach, beforeEach, describe, expect, it, vi} from "vitest";

import {
  persistFocusModeDefault,
  persistFocusThemeDefault,
  readFocusModeDefault,
  readFocusThemeDefault,
} from "./reader-preferences";

describe("reader preferences", () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => vi.restoreAllMocks());

  it("persists and restores focus settings", () => {
    persistFocusModeDefault(true);
    persistFocusThemeDefault("dark");

    expect(readFocusModeDefault()).toBe(true);
    expect(readFocusThemeDefault()).toBe("dark");
  });

  it("uses safe defaults for missing or invalid values", () => {
    localStorage.setItem("readvideo.reader.focusMode", "yes");
    localStorage.setItem("readvideo.reader.focusTheme", "sepia");
    expect(readFocusModeDefault()).toBe(false);
    expect(readFocusThemeDefault()).toBe("light");
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
    expect(() => persistFocusModeDefault(true)).not.toThrow();
  });
});
