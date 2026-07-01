import {TestBed} from "@angular/core/testing";
import {describe, expect, it} from "vitest";

import {ReaderFacade} from "../../data-access/reader-facade/reader.facade";
import {ReaderLibraryComponent} from "./reader-library.component";

describe("ReaderLibraryComponent", () => {
  it("uses the page-scoped reader facade", async () => {
    const reader = {};
    await TestBed.configureTestingModule({imports: [ReaderLibraryComponent]})
      .overrideComponent(ReaderLibraryComponent, {
        set: {template: "", providers: [{provide: ReaderFacade, useValue: reader}]},
      }).compileComponents();
    const fixture = TestBed.createComponent(ReaderLibraryComponent);
    expect(fixture.componentInstance.reader).toBe(reader);
  });
});
