import {ReaderFocusTheme, ReaderTextSize, ReaderWidth} from "../../models/reader-types/reader.types";

const FOCUS_MODE_STORAGE_KEY = "readvideo.reader.focusMode";
const FOCUS_THEME_STORAGE_KEY = "readvideo.reader.focusTheme";
const READER_WIDTH_STORAGE_KEY = "readvideo.reader.width";
const READER_TEXT_SIZE_STORAGE_KEY = "readvideo.reader.textSize";

export function readFocusModeDefault(): boolean {
  return readStorage(FOCUS_MODE_STORAGE_KEY) === "true";
}

export function persistFocusModeDefault(enabled: boolean): void {
  writeStorage(FOCUS_MODE_STORAGE_KEY, enabled ? "true" : "false");
}

export function readFocusThemeDefault(): ReaderFocusTheme {
  return readStorage(FOCUS_THEME_STORAGE_KEY) === "dark" ? "dark" : "light";
}

export function persistFocusThemeDefault(theme: ReaderFocusTheme): void {
  writeStorage(FOCUS_THEME_STORAGE_KEY, theme);
}

export function readReaderWidthDefault(): ReaderWidth {
  return readStorage(READER_WIDTH_STORAGE_KEY) === "wide" ? "wide" : "standard";
}

export function persistReaderWidthDefault(width: ReaderWidth): void {
  writeStorage(READER_WIDTH_STORAGE_KEY, width);
}

export function readReaderTextSizeDefault(): ReaderTextSize {
  return readStorage(READER_TEXT_SIZE_STORAGE_KEY) === "large" ? "large" : "standard";
}

export function persistReaderTextSizeDefault(size: ReaderTextSize): void {
  writeStorage(READER_TEXT_SIZE_STORAGE_KEY, size);
}

function readStorage(key: string): string | null {
  try {
    return typeof localStorage === "undefined" ? null : localStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeStorage(key: string, value: string): void {
  try {
    if (typeof localStorage !== "undefined") localStorage.setItem(key, value);
  } catch {
    // The in-memory preference still works when browser storage is unavailable.
  }
}
