import {FavoriteSummary, MarkdownFile} from "../../../../shared/models/readvideo-types/readvideo.types";
import {formatBytes} from "../../../../shared/utils/format/format";
import {hasTag, tagsFor} from "../../../../shared/utils/tags/tags";
import {LibraryMode, LibrarySort, ReaderLibraryItem} from "../../models/reader-types/reader.types";

export function filterFavorites(
  favorites: FavoriteSummary[],
  folderId: string,
  activeTag: string,
  query: string,
  sort: LibrarySort,
): FavoriteSummary[] {
  const needle = query.trim().toLocaleLowerCase();
  const matches = favorites.filter((item) => {
    const inFolder = folderId === "all"
      || (folderId === "unfiled" && !item.folder_id)
      || String(item.folder_id) === folderId;
    if (!inFolder || (activeTag !== "all" && !hasTag(tagsFor(item), activeTag))) return false;
    if (!needle) return true;
    return [
      favoriteTitle(item),
      item.url,
      item.summary,
      item.markdown_path,
      item.folder_name,
      tagsFor(item).join(" "),
    ].join(" ").toLocaleLowerCase().includes(needle);
  });
  return sortFavorites(matches, sort);
}

export function filterFiles(files: MarkdownFile[], query: string, sort: LibrarySort): MarkdownFile[] {
  const needle = query.trim().toLocaleLowerCase();
  const matches = files.filter((file) => (
    !needle || [file.name, file.path, file.modified_at].join(" ").toLocaleLowerCase().includes(needle)
  ));
  return sortFiles(matches, sort);
}

export function libraryItems(
  mode: LibraryMode,
  favorites: FavoriteSummary[],
  files: MarkdownFile[],
): ReaderLibraryItem[] {
  const favoriteItems = mode === "all" || mode === "favorites"
    ? favorites.map((favorite) => ({
      key: `favorite:${favorite.id}`,
      kind: "favorite" as const,
      path: favorite.markdown_path || "",
      title: favoriteTitle(favorite),
      typeLabel: "收藏笔记",
      context: favorite.folder_name || "未分类",
      preview: summaryPreview(favorite.summary) || favorite.url || "尚无内容摘要",
      tags: tagsFor(favorite),
      favorite,
      file: null,
    }))
    : [];
  const favoritePaths = new Set(favoriteItems.map((item) => item.path).filter(Boolean));
  const fileItems = mode === "all" || mode === "files"
    ? files
      .filter((file) => mode === "files" || !favoritePaths.has(file.path))
      .map((file) => ({
        key: `file:${file.path}`,
        kind: "file" as const,
        path: file.path,
        title: file.name,
        typeLabel: "本地文件",
        context: `${formatBytes(file.size_bytes)} · ${file.modified_at}`,
        preview: file.path,
        tags: [],
        favorite: null,
        file,
      }))
    : [];
  return [
    ...favoriteItems,
    ...fileItems,
  ];
}

export function favoriteTitle(item: FavoriteSummary): string {
  return item.title || item.url || item.task_id;
}

function summaryPreview(summary: string): string {
  return summary.replace(/\s+/g, " ").trim();
}

function sortFavorites(items: FavoriteSummary[], sort: LibrarySort): FavoriteSummary[] {
  return [...items].sort((first, second) => {
    if (sort === "title") return compareText(favoriteTitle(first), favoriteTitle(second));
    if (sort === "folder") {
      return compareText(first.folder_name || "未分类", second.folder_name || "未分类")
        || compareText(favoriteTitle(first), favoriteTitle(second));
    }
    if (sort === "path") return compareText(first.markdown_path || "", second.markdown_path || "");
    return dateValue(second.updated_at || second.created_at) - dateValue(first.updated_at || first.created_at);
  });
}

function sortFiles(items: MarkdownFile[], sort: LibrarySort): MarkdownFile[] {
  return [...items].sort((first, second) => {
    if (sort === "title" || sort === "folder") return compareText(first.name, second.name);
    if (sort === "path") return compareText(first.path, second.path);
    return dateValue(second.modified_at) - dateValue(first.modified_at);
  });
}

function compareText(first: string, second: string): number {
  return first.localeCompare(second, undefined, {numeric: true, sensitivity: "base"});
}

function dateValue(value: string): number {
  const date = Date.parse(value);
  return Number.isNaN(date) ? 0 : date;
}
