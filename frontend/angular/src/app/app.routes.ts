import {Routes} from "@angular/router";

import {FavoritesPageComponent} from "./pages/favorites-page/favorites-page.component";
import {HistoryPageComponent} from "./pages/history-page/history-page.component";
import {NewVideoPageComponent} from "./pages/new-video-page/new-video-page.component";
import {ReaderPageComponent} from "./pages/reader-page/reader-page.component";

export const routes: Routes = [
  {path: "", component: NewVideoPageComponent},
  {path: "history", component: HistoryPageComponent},
  {path: "favorites", component: FavoritesPageComponent},
  {path: "reader", component: ReaderPageComponent},
  {path: "**", redirectTo: ""},
];
