import {TestBed} from "@angular/core/testing";
import {describe, expect, it, vi} from "vitest";

import {ReaderPageComponent} from "./reader-page.component";
import {ReaderFacade} from "../../data-access/reader-facade/reader.facade";

describe("ReaderPageComponent", () => {
  it("initializes its page facade", async () => {
    const reader = {initialize: vi.fn()};
    await TestBed.configureTestingModule({imports: [ReaderPageComponent]})
      .overrideComponent(ReaderPageComponent, {
        set: {template: "", providers: [{provide: ReaderFacade, useValue: reader}]},
      }).compileComponents();
    const fixture = TestBed.createComponent(ReaderPageComponent);
    fixture.detectChanges();

    expect(fixture.componentInstance.reader).toBe(reader);
    expect(reader.initialize).toHaveBeenCalledOnce();
  });
});
