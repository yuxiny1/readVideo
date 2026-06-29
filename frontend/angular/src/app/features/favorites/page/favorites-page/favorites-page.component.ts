import {CommonModule} from "@angular/common";
import {ChangeDetectionStrategy, Component, inject, OnInit} from "@angular/core";
import {FormsModule} from "@angular/forms";

import {LibraryStore} from "../../../library/data-access/library-store/library.store";
import {FavoritesFacade} from "../../data-access/favorites-facade/favorites.facade";

@Component({
  selector: "rv-favorites-page",
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: "./favorites-page.component.html",
  styleUrl: "./favorites-page.component.scss",
  providers: [LibraryStore, FavoritesFacade],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FavoritesPageComponent implements OnInit {
  readonly favoritesPage = inject(FavoritesFacade);

  ngOnInit(): void {
    this.favoritesPage.initialize();
  }
}
