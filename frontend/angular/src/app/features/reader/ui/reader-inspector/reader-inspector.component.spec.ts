import {TestBed} from "@angular/core/testing";
import {describe, expect, it} from "vitest";

import {ReaderInspectorComponent} from "./reader-inspector.component";

describe("ReaderInspectorComponent", () => {
  it("receives reader state from its smart container", async () => {
    const reader = {};
    await TestBed.configureTestingModule({imports: [ReaderInspectorComponent]})
      .overrideComponent(ReaderInspectorComponent, {
        set: {template: ""},
      }).compileComponents();
    const fixture = TestBed.createComponent(ReaderInspectorComponent);
    fixture.componentRef.setInput("reader", reader);
    expect(fixture.componentInstance.reader()).toBe(reader);
  });
});
