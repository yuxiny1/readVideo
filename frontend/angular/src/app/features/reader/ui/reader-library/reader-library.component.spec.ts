import {TestBed} from "@angular/core/testing";
import {describe, expect, it} from "vitest";

import {ReaderLibraryComponent} from "./reader-library.component";

describe("ReaderLibraryComponent", () => {
  it("receives reader state from its smart container", async () => {
    const reader = {};
    await TestBed.configureTestingModule({imports: [ReaderLibraryComponent]})
      .overrideComponent(ReaderLibraryComponent, {
        set: {template: ""},
      }).compileComponents();
    const fixture = TestBed.createComponent(ReaderLibraryComponent);
    fixture.componentRef.setInput("reader", reader);
    expect(fixture.componentInstance.reader()).toBe(reader);
  });
});
