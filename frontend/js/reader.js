import {api} from "./api.js";
import {escapeHtml} from "./format.js";
import {renderMarkdown} from "./markdown.js";


const elements = {
  status: document.querySelector("#reader-status"),
  count: document.querySelector("#reader-count"),
  search: document.querySelector("#reader-search"),
  folderFilter: document.querySelector("#reader-folder-filter"),
  favorites: document.querySelector("#reader-favorites"),
  title: document.querySelector("#reader-title"),
  download: document.querySelector("#reader-download"),
  folderPicker: document.querySelector("#reader-folder-picker"),
  folderSelect: document.querySelector("#reader-folder-select"),
  path: document.querySelector("#reader-path"),
  content: document.querySelector("#reader-content"),
};

const state = {
  favorites: [],
  folders: [],
  activeFavorite: null,
  query: "",
};


async function init() {
  await Promise.all([loadFolders(), loadFavorites()]);
  renderFolderFilter();
  renderFavoriteList();

  const params = new URLSearchParams(window.location.search);
  const favoriteId = params.get("favorite_id");
  const path = params.get("path");
  if (favoriteId) {
    await openFavorite(favoriteId);
  } else if (path) {
    await openPath(path);
  }
}


async function loadFolders() {
  state.folders = await api("/api/favorites/folders");
}


async function loadFavorites() {
  state.favorites = await api("/api/favorites");
}


function renderFolderFilter() {
  elements.folderFilter.innerHTML = `
    <option value="all">All</option>
    <option value="unfiled">Unfiled</option>
    ${state.folders.map((folder) => `<option value="${folder.id}">${escapeHtml(folder.name)}</option>`).join("")}
  `;
}


function renderFavoriteList() {
  const favorites = filteredFavorites();
  elements.count.textContent = `${favorites.length} notes`;

  if (!favorites.length) {
    elements.favorites.innerHTML = '<div class="empty-state">No matching favorite notes.</div>';
    return;
  }

  elements.favorites.innerHTML = favorites.map((item) => `
    <button class="reader-note ${state.activeFavorite?.id === item.id ? "active" : ""}" type="button" data-id="${item.id}">
      <strong>${escapeHtml(item.title || item.url || item.task_id)}</strong>
      <span>${escapeHtml(item.folder_name || "Unfiled")}</span>
    </button>
  `).join("");
}


function filteredFavorites() {
  const query = state.query.trim().toLowerCase();
  const folder = elements.folderFilter.value || "all";

  return state.favorites.filter((item) => {
    const folderMatches = folder === "all"
      || (folder === "unfiled" && !item.folder_id)
      || String(item.folder_id) === folder;
    if (!folderMatches) return false;
    if (!query) return true;

    return [
      item.title,
      item.summary,
      item.url,
      item.markdown_path,
      item.folder_name,
    ].join(" ").toLowerCase().includes(query);
  });
}


async function openFavorite(itemId) {
  setStatus("Loading", "muted");
  const item = state.favorites.find((favorite) => String(favorite.id) === String(itemId));
  state.activeFavorite = item || null;
  renderFavoriteList();

  try {
    const document = await api(`/api/favorites/${encodeURIComponent(itemId)}/markdown`);
    renderDocument(document, item);
  } catch (error) {
    renderError(error.message);
  }
}


async function openPath(path) {
  setStatus("Loading", "muted");
  state.activeFavorite = null;
  renderFavoriteList();

  try {
    const document = await api(`/api/markdown_files/read?path=${encodeURIComponent(path)}`);
    renderDocument(document, null);
  } catch (error) {
    renderError(error.message);
  }
}


function renderDocument(document, favorite) {
  const title = favorite?.title || document.name;
  elements.title.textContent = title;
  elements.path.textContent = document.path;
  elements.content.innerHTML = renderMarkdown(document.content);
  elements.download.href = `/api/markdown_files/download?path=${encodeURIComponent(document.path)}`;
  elements.download.classList.remove("hidden");
  renderFolderPicker(favorite);
  setStatus("Open", "ok");
}


function renderFolderPicker(favorite) {
  if (!favorite) {
    elements.folderPicker.classList.add("hidden");
    elements.folderSelect.innerHTML = "";
    return;
  }

  elements.folderPicker.classList.remove("hidden");
  elements.folderSelect.innerHTML = `
    <option value="">Unfiled</option>
    ${state.folders.map((folder) => `
      <option value="${folder.id}" ${favorite.folder_id === folder.id ? "selected" : ""}>${escapeHtml(folder.name)}</option>
    `).join("")}
  `;
}


function renderError(message) {
  elements.title.textContent = "Could not open Markdown";
  elements.path.textContent = "";
  elements.download.classList.add("hidden");
  elements.folderPicker.classList.add("hidden");
  elements.content.innerHTML = `<div class="empty-state">${escapeHtml(message)}</div>`;
  setStatus("Error", "error");
}


function setStatus(text, kind) {
  elements.status.textContent = text;
  elements.status.className = `pill ${kind}`;
}


async function assignActiveFavoriteFolder() {
  if (!state.activeFavorite) return;
  const folderId = elements.folderSelect.value ? Number(elements.folderSelect.value) : null;
  const updated = await api(`/api/favorites/${encodeURIComponent(state.activeFavorite.id)}/folder`, {
    method: "PATCH",
    body: JSON.stringify({folder_id: folderId}),
  });
  state.favorites = state.favorites.map((item) => item.id === updated.id ? updated : item);
  state.activeFavorite = updated;
  renderFolderPicker(updated);
  renderFavoriteList();
}


elements.search.addEventListener("input", () => {
  state.query = elements.search.value;
  renderFavoriteList();
});
elements.folderFilter.addEventListener("change", renderFavoriteList);
elements.favorites.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-id]");
  if (!button) return;
  await openFavorite(button.dataset.id);
});
elements.folderSelect.addEventListener("change", assignActiveFavoriteFolder);

init();
