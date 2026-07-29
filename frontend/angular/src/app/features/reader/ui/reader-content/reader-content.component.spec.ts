import {TestBed} from "@angular/core/testing";
import {describe, expect, it} from "vitest";

import {ReaderContentComponent} from "./reader-content.component";

describe("ReaderContentComponent", () => {
  it("receives reader state from its smart container", async () => {
    const reader = {};
    await TestBed.configureTestingModule({imports: [ReaderContentComponent]})
      .overrideComponent(ReaderContentComponent, {
        set: {template: ""},
      }).compileComponents();
    const fixture = TestBed.createComponent(ReaderContentComponent);
    fixture.componentRef.setInput("reader", reader);
    expect(fixture.componentInstance.reader()).toBe(reader);
  });
});
