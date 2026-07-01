import {TestBed} from "@angular/core/testing";
import {describe, expect, it} from "vitest";

import {ReaderFacade} from "../../data-access/reader-facade/reader.facade";
import {ReaderDocumentToolbarComponent} from "./reader-document-toolbar.component";

describe("ReaderDocumentToolbarComponent", () => {
  it("uses the page-scoped reader facade", async () => {
    const reader = {};
    await TestBed.configureTestingModule({imports: [ReaderDocumentToolbarComponent]})
      .overrideComponent(ReaderDocumentToolbarComponent, {
        set: {template: "", providers: [{provide: ReaderFacade, useValue: reader}]},
      }).compileComponents();
    const fixture = TestBed.createComponent(ReaderDocumentToolbarComponent);
    expect(fixture.componentInstance.reader).toBe(reader);
  });
});
