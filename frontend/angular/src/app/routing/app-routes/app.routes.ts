import {Routes} from "@angular/router";

export const routes: Routes = [
  {
    path: "",
    loadComponent: () => import("../../features/new-video/page/new-video-page/new-video-page.component")
      .then((module) => module.NewVideoPageComponent),
  },
  {
    path: "history",
    loadComponent: () => import("../../features/history/page/history-page/history-page.component")
      .then((module) => module.HistoryPageComponent),
  },
  {
    path: "favorites",
    loadComponent: () => import("../../features/favorites/page/favorites-page/favorites-page.component")
      .then((module) => module.FavoritesPageComponent),
  },
  {
    path: "reader",
    loadComponent: () => import("../../features/reader/page/reader-page/reader-page.component")
      .then((module) => module.ReaderPageComponent),
  },
  {path: "**", redirectTo: ""},
];
