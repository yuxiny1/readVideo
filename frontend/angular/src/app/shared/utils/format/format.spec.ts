import {describe, expect, it} from "vitest";

import {formatBytes, formatElapsed, formatEta, formatSpeed, statusLabel} from "./format";

describe("format helpers", () => {
  it("formats status labels", () => {
    expect(statusLabel("organizing_notes")).toBe("organizing notes");
    expect(statusLabel()).toBe("idle");
  });

  it("formats valid and invalid elapsed ranges", () => {
    expect(formatElapsed({created_at: "2026-01-01T00:00:00Z", completed_at: "2026-01-01T00:01:05Z"}))
      .toBe("1m 5s");
    expect(formatElapsed({created_at: "2026-01-01T00:00:00Z", completed_at: "2026-01-01T00:00:12Z"}))
      .toBe("12s");
    expect(formatElapsed({created_at: "invalid"})).toBe("0s");
  });

  it("formats byte values and transfer rates", () => {
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(1536)).toBe("1.5 KB");
    expect(formatBytes(1024 ** 3)).toBe("1.0 GB");
    expect(formatBytes(0)).toBe("-");
    expect(formatSpeed(2048)).toBe("2.0 KB/s");
    expect(formatSpeed("bad")).toBe("");
  });

  it("formats ETA values", () => {
    expect(formatEta(14.6)).toBe("15s");
    expect(formatEta(125)).toBe("2m 5s");
    expect(formatEta(-1)).toBe("");
  });
});
