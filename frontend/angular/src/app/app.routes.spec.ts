import {Type} from "@angular/core";
import {describe, expect, it} from "vitest";

import {FavoritesPageComponent} from "./pages/favorites-page/favorites-page.component";
import {HistoryPageComponent} from "./pages/history-page/history-page.component";
import {NewVideoPageComponent} from "./pages/new-video-page/new-video-page.component";
import {ReaderPageComponent} from "./pages/reader-page/reader-page.component";
import {routes} from "./app.routes";

describe("application routes", () => {
  it("defines lazy routes for every primary page and a fallback", () => {
    expect(routes.map((route) => route.path)).toEqual(["", "history", "favorites", "reader", "**"]);
    expect(routes.at(-1)?.redirectTo).toBe("");
    expect(routes.slice(0, 4).every((route) => typeof route.loadComponent === "function")).toBe(true);
  });

  it("loads each page component", async () => {
    const loaded = await Promise.all(routes.slice(0, 4).map(async (route) => (
      await (route.loadComponent?.() as Promise<Type<unknown>>)
    )));
    expect(loaded).toEqual([
      NewVideoPageComponent,
      HistoryPageComponent,
      FavoritesPageComponent,
      ReaderPageComponent,
    ]);
  });
});
