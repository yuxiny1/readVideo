import {Routes} from "@angular/router";

export const routes: Routes = [
  {
    path: "",
    loadComponent: () => import("./pages/new-video-page/new-video-page.component")
      .then((module) => module.NewVideoPageComponent),
  },
  {
    path: "history",
    loadComponent: () => import("./pages/history-page/history-page.component")
      .then((module) => module.HistoryPageComponent),
  },
  {
    path: "favorites",
    loadComponent: () => import("./pages/favorites-page/favorites-page.component")
      .then((module) => module.FavoritesPageComponent),
  },
  {
    path: "reader",
    loadComponent: () => import("./pages/reader-page/reader-page.component")
      .then((module) => module.ReaderPageComponent),
  },
  {path: "**", redirectTo: ""},
];
