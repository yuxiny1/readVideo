import {TestBed} from "@angular/core/testing";
import {describe, expect, it} from "vitest";

import {ReaderDocumentToolbarComponent} from "./reader-document-toolbar.component";

describe("ReaderDocumentToolbarComponent", () => {
  it("receives reader state from its smart container", async () => {
    const reader = {};
    await TestBed.configureTestingModule({imports: [ReaderDocumentToolbarComponent]})
      .overrideComponent(ReaderDocumentToolbarComponent, {
        set: {template: ""},
      }).compileComponents();
    const fixture = TestBed.createComponent(ReaderDocumentToolbarComponent);
    fixture.componentRef.setInput("reader", reader);
    expect(fixture.componentInstance.reader()).toBe(reader);
  });
});
