import {TestBed} from "@angular/core/testing";
import {describe, expect, it, vi} from "vitest";

import {HistoryPageComponent} from "./history-page.component";
import {HistoryFacade} from "../../data-access/history-facade/history.facade";

describe("HistoryPageComponent", () => {
  it("initializes its page facade", async () => {
    const history = {initialize: vi.fn()};
    await TestBed.configureTestingModule({imports: [HistoryPageComponent]})
      .overrideComponent(HistoryPageComponent, {
        set: {template: "", providers: [{provide: HistoryFacade, useValue: history}]},
      }).compileComponents();
    const fixture = TestBed.createComponent(HistoryPageComponent);
    fixture.detectChanges();

    expect(fixture.componentInstance.history).toBe(history);
    expect(history.initialize).toHaveBeenCalledOnce();
  });
});
