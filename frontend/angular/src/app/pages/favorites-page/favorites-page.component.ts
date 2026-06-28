import {CommonModule} from "@angular/common";
import {ChangeDetectionStrategy, Component, inject, OnInit} from "@angular/core";
import {FormsModule} from "@angular/forms";

import {LibraryStore} from "../../features/library/data-access/library.store";
import {FavoritesFacade} from "./favorites.facade";

@Component({
  selector: "rv-favorites-page",
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: "./favorites-page.component.html",
  providers: [LibraryStore, FavoritesFacade],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FavoritesPageComponent implements OnInit {
  readonly favoritesPage = inject(FavoritesFacade);

  ngOnInit(): void {
    this.favoritesPage.initialize();
  }
}
