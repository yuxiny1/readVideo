import {FavoriteSummary, MarkdownFile} from "../../types/readvideo.types";

export type LibraryMode = "all" | "favorites" | "files";
export type LibrarySort = "recent" | "title" | "folder" | "path";
export type ReaderWidth = "standard" | "wide";
export type ReaderTextSize = "standard" | "large";
export type ReaderViewMode = "rendered" | "markdown";
export type ReaderFocusTheme = "light" | "dark";

export interface ReaderHeading {
  id: string;
  level: number;
  title: string;
}

export interface ReaderLibraryItem {
  kind: "favorite" | "file";
  path: string;
  favorite: FavoriteSummary | null;
  file: MarkdownFile | null;
}
