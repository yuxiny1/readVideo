import {TestBed} from "@angular/core/testing";
import {describe, expect, it} from "vitest";

import {ReaderFacade} from "../../data-access/reader-facade/reader.facade";
import {ReaderContentComponent} from "./reader-content.component";

describe("ReaderContentComponent", () => {
  it("uses the page-scoped reader facade", async () => {
    const reader = {};
    await TestBed.configureTestingModule({imports: [ReaderContentComponent]})
      .overrideComponent(ReaderContentComponent, {
        set: {template: "", providers: [{provide: ReaderFacade, useValue: reader}]},
      }).compileComponents();
    const fixture = TestBed.createComponent(ReaderContentComponent);
    expect(fixture.componentInstance.reader).toBe(reader);
  });
});
