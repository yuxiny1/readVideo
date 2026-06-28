import {TestBed} from "@angular/core/testing";
import {describe, expect, it, vi} from "vitest";

import {FavoritesPageComponent} from "./favorites-page.component";
import {FavoritesFacade} from "./favorites.facade";

describe("FavoritesPageComponent", () => {
  it("initializes its page facade", async () => {
    const facade = {initialize: vi.fn()};
    await TestBed.configureTestingModule({imports: [FavoritesPageComponent]})
      .overrideComponent(FavoritesPageComponent, {
        set: {template: "", providers: [{provide: FavoritesFacade, useValue: facade}]},
      }).compileComponents();
    const fixture = TestBed.createComponent(FavoritesPageComponent);
    fixture.detectChanges();

    expect(fixture.componentInstance.favoritesPage).toBe(facade);
    expect(facade.initialize).toHaveBeenCalledOnce();
  });
});
