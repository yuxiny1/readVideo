import {TestBed} from "@angular/core/testing";
import {provideRouter} from "@angular/router";
import {describe, expect, it} from "vitest";

import {AppComponent} from "./app.component";

describe("AppComponent", () => {
  it("creates the application shell with primary navigation", async () => {
    await TestBed.configureTestingModule({
      imports: [AppComponent],
      providers: [provideRouter([])],
    }).compileComponents();

    const fixture = TestBed.createComponent(AppComponent);
    fixture.detectChanges();

    expect(fixture.componentInstance).toBeTruthy();
    expect(fixture.nativeElement.querySelectorAll("nav a").length).toBeGreaterThanOrEqual(4);
    expect(fixture.nativeElement.querySelector("router-outlet")).toBeTruthy();
  });
});
