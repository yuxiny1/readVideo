import {api} from "./api.js";
import {escapeHtml} from "./format.js";


const elements = {
  count: document.querySelector("#favorites-count"),
  list: document.querySelector("#favorites-list"),
  refresh: document.querySelector("#refresh-favorites"),
  folderForm: document.querySelector("#md-folder-form"),
  folder: document.querySelector("#md-folder"),
  useDefaultFolder: document.querySelector("#use-default-folder"),
  fileCount: document.querySelector("#md-count"),
  files: document.querySelector("#md-files"),
};

const state = {
  defaultNotesDir: "notes",
};


async function loadConfig() {
  try {
    const config = await api("/app_config");
    state.defaultNotesDir = config.notes_dir || "notes";
    elements.folder.placeholder = state.defaultNotesDir;
    if (!elements.folder.value.trim()) {
      elements.folder.value = state.defaultNotesDir;
    }
  } catch {
    elements.folder.value = state.defaultNotesDir;
  }
}


async function loadFavorites() {
  elements.count.textContent = "Loading";
  try {
    const favorites = await api("/api/favorites");
    elements.count.textContent = `${favorites.length} saved`;

    if (!favorites.length) {
      elements.list.innerHTML = '<div class="empty-state">No favorite summaries yet. Add them from History.</div>';
      return;
    }

    elements.list.innerHTML = favorites.map(renderFavorite).join("");
  } catch (error) {
    elements.count.textContent = "Error";
    elements.list.innerHTML = `<div class="empty-state">${escapeHtml(error.message)}</div>`;
  }
}


function renderFavorite(item) {
  const title = item.title || item.url || item.task_id;
  return `
    <article class="favorite-card" data-id="${item.id}">
      <div class="history-card-header">
        <div>
          <h2>${escapeHtml(title)}</h2>
          <a class="watch-url" href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer">${escapeHtml(item.url || "No URL")}</a>
        </div>
        <span class="pill ok">Favorite</span>
      </div>

      <section class="favorite-detail">
        <h3>Title</h3>
        <p>${escapeHtml(title)}</p>
      </section>

      <section class="favorite-detail">
        <h3>Content</h3>
        <pre class="summary-preview">${escapeHtml(item.summary || "No summary saved.")}</pre>
      </section>

      <dl class="path-list">
        ${pathRow("Source Link", item.url)}
        ${pathRow("Markdown", item.markdown_path)}
        ${pathRow("Folder", item.notes_dir)}
      </dl>

      <div class="card-actions">
        ${item.markdown_path ? `<a class="quiet-link small-link" href="/api/markdown_files/download?path=${encodeURIComponent(item.markdown_path)}">Download MD</a>` : ""}
        ${item.notes_dir ? `<button class="secondary-button small-button" type="button" data-action="open-folder" data-folder="${escapeHtml(item.notes_dir)}">Show Folder</button>` : ""}
        <button class="danger-button small-button" type="button" data-action="delete">Remove</button>
      </div>
    </article>
  `;
}


function pathRow(label, value) {
  return `
    <div>
      <dt>${escapeHtml(label)}</dt>
      <dd><code>${escapeHtml(value || "-")}</code></dd>
    </div>
  `;
}


async function loadMarkdownFiles(directory = elements.folder.value.trim() || state.defaultNotesDir) {
  elements.fileCount.textContent = "Loading";
  try {
    const files = await api(`/api/markdown_files?directory=${encodeURIComponent(directory)}`);
    elements.fileCount.textContent = `${files.length} files`;
    elements.folder.value = directory;

    if (!files.length) {
      elements.files.innerHTML = '<div class="empty-state">No Markdown files in this folder.</div>';
      return;
    }

    elements.files.innerHTML = files.map(renderMarkdownFile).join("");
  } catch (error) {
    elements.fileCount.textContent = "Error";
    elements.files.innerHTML = `<div class="empty-state">${escapeHtml(error.message)}</div>`;
  }
}


function renderMarkdownFile(file) {
  return `
    <article class="file-row">
      <div>
        <p class="watch-title">${escapeHtml(file.name)}</p>
        <code>${escapeHtml(file.path)}</code>
        <div class="history-meta">
          <span>${escapeHtml(formatBytes(file.size_bytes))}</span>
          <span>${escapeHtml(file.modified_at)}</span>
        </div>
      </div>
      <a class="quiet-link small-link" href="/api/markdown_files/download?path=${encodeURIComponent(file.path)}">Download</a>
    </article>
  `;
}


function formatBytes(value) {
  const size = Number(value) || 0;
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}


async function handleFavoriteClick(event) {
  const button = event.target.closest("button[data-action]");
  if (!button) return;

  const card = button.closest(".favorite-card");
  if (button.dataset.action === "delete") {
    await api(`/api/favorites/${encodeURIComponent(card.dataset.id)}`, {method: "DELETE"});
    await loadFavorites();
  }

  if (button.dataset.action === "open-folder") {
    await loadMarkdownFiles(button.dataset.folder);
  }
}


async function handleFolderSubmit(event) {
  event.preventDefault();
  await loadMarkdownFiles();
}


elements.refresh.addEventListener("click", loadFavorites);
elements.list.addEventListener("click", handleFavoriteClick);
elements.folderForm.addEventListener("submit", handleFolderSubmit);
elements.useDefaultFolder.addEventListener("click", () => loadMarkdownFiles(state.defaultNotesDir));

await loadConfig();
loadFavorites();
loadMarkdownFiles();
