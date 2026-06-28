import {describe, expect, it, vi} from "vitest";

import {AppComponent} from "./app/app.component";

const {bootstrapApplicationMock} = vi.hoisted(() => ({
  bootstrapApplicationMock: vi.fn((
    _component: {name: string},
    _config: {providers: unknown[]},
  ) => Promise.resolve({})),
}));

vi.mock("@angular/platform-browser", async (importOriginal) => ({
  ...await importOriginal<typeof import("@angular/platform-browser")>(),
  bootstrapApplication: bootstrapApplicationMock,
}));

describe("application bootstrap", () => {
  it("starts the root component with HTTP and router providers", async () => {
    await import("./main");

    expect(bootstrapApplicationMock).toHaveBeenCalledOnce();
    const [component, config] = bootstrapApplicationMock.mock.calls[0];
    expect(component).toBe(AppComponent);
    expect(config.providers).toHaveLength(2);
  });
});
