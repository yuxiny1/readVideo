import {describe, expect, it} from "vitest";

import {errorMessage} from "./errors";

describe("errorMessage", () => {
  it("returns an Error message", () => {
    expect(errorMessage(new Error("network unavailable"))).toBe("network unavailable");
  });

  it("normalizes non-Error values", () => {
    expect(errorMessage(404)).toBe("404");
    expect(errorMessage(null)).toBe("null");
  });
});
