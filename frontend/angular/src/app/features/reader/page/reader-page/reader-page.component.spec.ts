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

  it("exits focus mode when Escape is pressed", async () => {
    const toggleFocusMode = vi.fn();
    const reader = {
      initialize: vi.fn(),
      document: {
        status: vi.fn(() => "空闲"),
        focusMode: vi.fn(() => true),
        focusTheme: vi.fn(() => "light"),
        readerWidth: vi.fn(() => "standard"),
        path: vi.fn(() => ""),
        toggleFocusMode,
      },
      libraryCount: vi.fn(() => "0 篇收藏 · 0 个文件"),
      canOpenPrevious: vi.fn(() => false),
      canOpenNext: vi.fn(() => false),
    };
    await TestBed.configureTestingModule({imports: [ReaderPageComponent]})
      .overrideComponent(ReaderPageComponent, {
        set: {template: "", providers: [{provide: ReaderFacade, useValue: reader}]},
      }).compileComponents();
    const fixture = TestBed.createComponent(ReaderPageComponent);

    fixture.componentInstance.exitFocusMode();

    expect(fixture.componentInstance.pageVm().canToggleFocus).toBe(true);
    expect(fixture.componentInstance.pageVm().focusButtonLabel).toBe("退出专注阅读");
    expect(toggleFocusMode).toHaveBeenCalledOnce();
  });
});
