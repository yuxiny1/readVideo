import {TestBed} from "@angular/core/testing";
import {describe, expect, it} from "vitest";

import {ReaderFacade} from "../../data-access/reader-facade/reader.facade";
import {ReaderInspectorComponent} from "./reader-inspector.component";

describe("ReaderInspectorComponent", () => {
  it("uses the page-scoped reader facade", async () => {
    const reader = {};
    await TestBed.configureTestingModule({imports: [ReaderInspectorComponent]})
      .overrideComponent(ReaderInspectorComponent, {
        set: {template: "", providers: [{provide: ReaderFacade, useValue: reader}]},
      }).compileComponents();
    const fixture = TestBed.createComponent(ReaderInspectorComponent);
    expect(fixture.componentInstance.reader).toBe(reader);
  });
});
