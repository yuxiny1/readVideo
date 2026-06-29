import {computed, inject} from "@angular/core";
import {tapResponse} from "@ngrx/operators";
import {patchState, signalStore, withComputed, withMethods, withState} from "@ngrx/signals";
import {rxMethod} from "@ngrx/signals/rxjs-interop";
import {concatMap, exhaustMap, forkJoin, map, pipe, switchMap, tap} from "rxjs";

import {ReadvideoApiService} from "../../../../core/api/readvideo-api/readvideo-api.service";
import {FavoriteFolder, FavoriteSummary, TagSummary} from "../../../../shared/models/readvideo-types/readvideo.types";
import {errorMessage} from "../../../../shared/utils/errors/errors";

interface LibraryState {
  favorites: FavoriteSummary[];
  folders: FavoriteFolder[];
  tags: TagSummary[];
  pendingRequests: number;
  error: string;
  notice: string;
}

export interface CreateFolderCommand {
  name: string;
  notes: string;
}

export interface UpdateFolderCommand {
  folderId: number;
  name: string;
  notes: string;
}

export interface AssignFolderCommand {
  favoriteId: number;
  folderId: number | null;
}

export interface UpdateFavoriteTagsCommand {
  favoriteId: number;
  tags: string[];
}

const initialState: LibraryState = {
  favorites: [],
  folders: [],
  tags: [],
  pendingRequests: 0,
  error: "",
  notice: "",
};

export const LibraryStore = signalStore(
  withState(initialState),
  withComputed(({favorites, folders, tags, pendingRequests}) => ({
    favoriteCount: computed(() => favorites().length),
    folderCount: computed(() => folders().length),
    tagCount: computed(() => tags().length),
    loading: computed(() => pendingRequests() > 0),
  })),
  withMethods((store, api = inject(ReadvideoApiService)) => {
    const beginRequest = () => patchState(store, (state) => ({
      pendingRequests: state.pendingRequests + 1,
      error: "",
      notice: "",
    }));
    const failRequest = (error: unknown) => patchState(store, {error: errorMessage(error)});
    const finishRequest = () => patchState(store, (state) => ({
      pendingRequests: Math.max(0, state.pendingRequests - 1),
    }));

    return {
      clearFeedback(): void {
        patchState(store, {error: "", notice: ""});
      },

      loadAll: rxMethod<void>(
        pipe(
          exhaustMap(() => {
            beginRequest();
            return forkJoin({
              favorites: api.favorites(),
              folders: api.favoriteFolders(),
              tags: api.tags(),
            }).pipe(
              tapResponse({
                next: ({favorites, folders, tags}) => patchState(store, {favorites, folders, tags}),
                error: failRequest,
                finalize: finishRequest,
              }),
            );
          }),
        ),
      ),

      createFolder: rxMethod<CreateFolderCommand>(
        pipe(
          tap(beginRequest),
          concatMap(({name, notes}) => api.addFavoriteFolder(name, notes).pipe(
            switchMap(() => api.favoriteFolders()),
            tapResponse({
              next: (folders) => patchState(store, {folders, notice: "Folder created"}),
              error: failRequest,
              finalize: finishRequest,
            }),
          )),
        ),
      ),

      updateFolder: rxMethod<UpdateFolderCommand>(
        pipe(
          tap(beginRequest),
          concatMap(({folderId, name, notes}) => api.updateFavoriteFolder(folderId, name, notes).pipe(
            switchMap((updated) => api.favorites().pipe(map((favorites) => ({updated, favorites})))),
            tapResponse({
              next: ({updated, favorites}) => patchState(store, (state) => ({
                favorites,
                folders: state.folders.map((folder) => folder.id === updated.id ? updated : folder),
                notice: "Folder updated",
              })),
              error: failRequest,
              finalize: finishRequest,
            }),
          )),
        ),
      ),

      assignFolder: rxMethod<AssignFolderCommand>(
        pipe(
          tap(beginRequest),
          concatMap(({favoriteId, folderId}) => api.assignFavoriteFolder(favoriteId, folderId).pipe(
            switchMap((updated) => api.favoriteFolders().pipe(map((folders) => ({updated, folders})))),
            tapResponse({
              next: ({updated, folders}) => patchState(store, (state) => ({
                favorites: replaceFavorite(state.favorites, updated),
                folders,
              })),
              error: failRequest,
              finalize: finishRequest,
            }),
          )),
        ),
      ),

      deleteFavorite: rxMethod<number>(
        pipe(
          tap(beginRequest),
          concatMap((favoriteId) => api.deleteFavorite(favoriteId).pipe(
            switchMap(() => forkJoin({
              favorites: api.favorites(),
              folders: api.favoriteFolders(),
              tags: api.tags(),
            })),
            tapResponse({
              next: ({favorites, folders, tags}) => patchState(store, {
                favorites,
                folders,
                tags,
                notice: "Favorite removed",
              }),
              error: failRequest,
              finalize: finishRequest,
            }),
          )),
        ),
      ),

      updateTags: rxMethod<UpdateFavoriteTagsCommand>(
        pipe(
          tap(beginRequest),
          concatMap(({favoriteId, tags}) => api.updateFavoriteTags(favoriteId, tags).pipe(
            switchMap((updated) => api.tags().pipe(map((allTags) => ({updated, allTags})))),
            tapResponse({
              next: ({updated, allTags}) => patchState(store, (state) => ({
                favorites: replaceFavorite(state.favorites, updated),
                tags: allTags,
                notice: "Tags saved",
              })),
              error: failRequest,
              finalize: finishRequest,
            }),
          )),
        ),
      ),
    };
  }),
);

function replaceFavorite(favorites: FavoriteSummary[], updated: FavoriteSummary): FavoriteSummary[] {
  return favorites.map((favorite) => favorite.id === updated.id ? updated : favorite);
}
