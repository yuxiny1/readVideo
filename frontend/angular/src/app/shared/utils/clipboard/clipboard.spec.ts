import {afterEach, describe, expect, it, vi} from "vitest";

import {copyTextToClipboard} from "./clipboard";

describe("copyTextToClipboard", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    Object.defineProperty(navigator, "clipboard", {configurable: true, value: undefined});
    Object.defineProperty(document, "execCommand", {configurable: true, value: undefined});
  });

  it("uses the async Clipboard API when available", async () => {
    const writeText = vi.fn(() => Promise.resolve());
    Object.defineProperty(navigator, "clipboard", {configurable: true, value: {writeText}});

    await copyTextToClipboard("hello");

    expect(writeText).toHaveBeenCalledWith("hello");
  });

  it("falls back to the legacy copy command when Clipboard API fails", async () => {
    const writeText = vi.fn(() => Promise.reject(new Error("denied")));
    const execCommand = vi.fn(() => true);
    Object.defineProperty(document, "execCommand", {configurable: true, value: execCommand});
    Object.defineProperty(navigator, "clipboard", {configurable: true, value: {writeText}});

    await copyTextToClipboard("fallback");

    expect(writeText).toHaveBeenCalledWith("fallback");
    expect(execCommand).toHaveBeenCalledWith("copy");
    expect(document.querySelector("textarea")).toBeNull();
  });

  it("falls back when writeText throws synchronously", async () => {
    const writeText = vi.fn(() => {
      throw new TypeError("Cannot read properties of undefined (reading 'writeText')");
    });
    const execCommand = vi.fn(() => true);
    Object.defineProperty(document, "execCommand", {configurable: true, value: execCommand});
    Object.defineProperty(navigator, "clipboard", {configurable: true, value: {writeText}});

    await copyTextToClipboard("synchronous failure");

    expect(execCommand).toHaveBeenCalledWith("copy");
    expect(document.querySelector("textarea")).toBeNull();
  });

  it("falls back when clipboard exists without writeText", async () => {
    const execCommand = vi.fn(() => true);
    Object.defineProperty(document, "execCommand", {configurable: true, value: execCommand});
    Object.defineProperty(navigator, "clipboard", {configurable: true, value: {}});

    await copyTextToClipboard("missing method");

    expect(execCommand).toHaveBeenCalledWith("copy");
  });

  it("reports a useful error when both copy methods fail", async () => {
    Object.defineProperty(navigator, "clipboard", {configurable: true, value: undefined});
    Object.defineProperty(document, "execCommand", {configurable: true, value: vi.fn(() => false)});

    await expect(copyTextToClipboard("nope")).rejects.toThrow("复制失败");
  });

  it("normalizes legacy copy exceptions to a useful error", async () => {
    Object.defineProperty(navigator, "clipboard", {configurable: true, value: undefined});
    Object.defineProperty(document, "execCommand", {
      configurable: true,
      value: vi.fn(() => {
        throw new DOMException("blocked");
      }),
    });

    await expect(copyTextToClipboard("blocked")).rejects.toThrow(
      "复制失败，请手动选择文本复制。",
    );
    expect(document.querySelector("textarea")).toBeNull();
  });
});
