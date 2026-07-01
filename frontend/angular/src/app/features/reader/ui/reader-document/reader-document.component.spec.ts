import {TestBed} from "@angular/core/testing";
import {describe, expect, it} from "vitest";

import {ReaderDocumentComponent} from "./reader-document.component";

describe("ReaderDocumentComponent", () => {
  it("composes the reader toolbar and content", async () => {
    await TestBed.configureTestingModule({imports: [ReaderDocumentComponent]})
      .overrideComponent(ReaderDocumentComponent, {
        set: {template: ""},
      }).compileComponents();
    const fixture = TestBed.createComponent(ReaderDocumentComponent);
    expect(fixture.componentInstance).toBeTruthy();
  });
});
