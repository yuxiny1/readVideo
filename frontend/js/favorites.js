import {api} from "./api.js";
import {escapeHtml} from "./format.js";


const elements = {
  count: document.querySelector("#favorites-count"),
  list: document.querySelector("#favorites-list"),
  refresh: document.querySelector("#refresh-favorites"),
  folderForm: document.querySelector("#favorite-folder-form"),
  folderName: document.querySelector("#favorite-folder-name"),
  folderNotes: document.querySelector("#favorite-folder-notes"),
  folderCount: document.querySelector("#folder-count"),
  folderList: document.querySelector("#favorite-folders"),
  readerStatus: document.querySelector("#reader-status"),
  readerPath: document.querySelector("#reader-path"),
  readerContent: document.querySelector("#reader-content"),
  mdFolderForm: document.querySelector("#md-folder-form"),
  mdFolder: document.querySelector("#md-folder"),
  useDefaultFolder: document.querySelector("#use-default-folder"),
  fileCount: document.querySelector("#md-count"),
  files: document.querySelector("#md-files"),
};

const state = {
  defaultNotesDir: "notes",
  favorites: [],
  folders: [],
  activeFolderId: "all",
};


async function loadConfig() {
  try {
    const config = await api("/app_config");
    state.defaultNotesDir = config.notes_dir || "notes";
    elements.mdFolder.placeholder = state.defaultNotesDir;
    if (!elements.mdFolder.value.trim()) {
      elements.mdFolder.value = state.defaultNotesDir;
    }
  } catch {
    elements.mdFolder.value = state.defaultNotesDir;
  }
}


async function loadFolders() {
  state.folders = await api("/api/favorites/folders");
  elements.folderCount.textContent = `${state.folders.length} folders`;
  renderFolders();
}


async function loadFavorites() {
  elements.count.textContent = "Loading";
  try {
    state.favorites = await api("/api/favorites");
    renderFavorites();
  } catch (error) {
    elements.count.textContent = "Error";
    elements.list.innerHTML = `<div class="empty-state">${escapeHtml(error.message)}</div>`;
  }
}


function renderFavorites() {
  const favorites = filteredFavorites();
  elements.count.textContent = `${favorites.length} shown / ${state.favorites.length} saved`;

  if (!favorites.length) {
    elements.list.innerHTML = '<div class="empty-state">No favorite summaries in this folder yet.</div>';
    return;
  }

  elements.list.innerHTML = favorites.map(renderFavorite).join("");
}


function filteredFavorites() {
  if (state.activeFolderId === "all") return state.favorites;
  if (state.activeFolderId === "unfiled") {
    return state.favorites.filter((item) => !item.folder_id);
  }
  return state.favorites.filter((item) => String(item.folder_id) === state.activeFolderId);
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
        <span class="pill ok">${escapeHtml(item.folder_name || "Unfiled")}</span>
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

      <div class="folder-picker">
        <label for="favorite-folder-${item.id}">Favorite Folder</label>
        <select id="favorite-folder-${item.id}" data-action="assign-folder">
          <option value="">Unfiled</option>
          ${state.folders.map((folder) => `
            <option value="${folder.id}" ${item.folder_id === folder.id ? "selected" : ""}>${escapeHtml(folder.name)}</option>
          `).join("")}
        </select>
      </div>

      <div class="card-actions">
        ${item.markdown_path ? `<button class="secondary-button small-button" type="button" data-action="read-favorite">Read MD</button>` : ""}
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


function renderFolders() {
  const counts = folderCounts();
  elements.folderList.innerHTML = `
    ${folderButton("all", "All", state.favorites.length)}
    ${folderButton("unfiled", "Unfiled", counts.unfiled)}
    ${state.folders.map((folder) => folderButton(String(folder.id), folder.name, counts[folder.id] || 0, folder.notes)).join("")}
  `;
}


function folderButton(id, name, count, notes = "") {
  const active = state.activeFolderId === id ? "active" : "";
  const deleteButton = id === "all" || id === "unfiled" ? "" : `
    <button class="danger-button small-button" type="button" data-action="delete-folder" data-folder-id="${escapeHtml(id)}">Delete</button>
  `;
  return `
    <div class="folder-item">
      <button class="folder-chip ${active}" type="button" data-action="filter-folder" data-folder-id="${escapeHtml(id)}">
        <span>${escapeHtml(name)}</span>
        <span>${count}</span>
      </button>
      ${notes ? `<p>${escapeHtml(notes)}</p>` : ""}
      ${deleteButton}
    </div>
  `;
}


function folderCounts() {
  const counts = {unfiled: 0};
  state.favorites.forEach((item) => {
    if (!item.folder_id) {
      counts.unfiled += 1;
      return;
    }
    counts[item.folder_id] = (counts[item.folder_id] || 0) + 1;
  });
  return counts;
}


async function loadMarkdownFiles(directory = elements.mdFolder.value.trim() || state.defaultNotesDir) {
  elements.fileCount.textContent = "Loading";
  try {
    const files = await api(`/api/markdown_files?directory=${encodeURIComponent(directory)}`);
    elements.fileCount.textContent = `${files.length} files`;
    elements.mdFolder.value = directory;

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
    <article class="file-row" data-path="${escapeHtml(file.path)}">
      <div>
        <p class="watch-title">${escapeHtml(file.name)}</p>
        <code>${escapeHtml(file.path)}</code>
        <div class="history-meta">
          <span>${escapeHtml(formatBytes(file.size_bytes))}</span>
          <span>${escapeHtml(file.modified_at)}</span>
        </div>
      </div>
      <div class="card-actions">
        <button class="secondary-button small-button" type="button" data-action="read-md-file">Read</button>
        <a class="quiet-link small-link" href="/api/markdown_files/download?path=${encodeURIComponent(file.path)}">Download</a>
      </div>
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
    renderFolders();
  }

  if (button.dataset.action === "open-folder") {
    await loadMarkdownFiles(button.dataset.folder);
  }

  if (button.dataset.action === "read-favorite") {
    await openFavoriteMarkdown(card.dataset.id);
  }
}


async function handleFavoriteChange(event) {
  const select = event.target.closest("select[data-action='assign-folder']");
  if (!select) return;

  const card = select.closest(".favorite-card");
  const folderId = select.value ? Number(select.value) : null;
  await api(`/api/favorites/${encodeURIComponent(card.dataset.id)}/folder`, {
    method: "PATCH",
    body: JSON.stringify({folder_id: folderId}),
  });
  await loadFavorites();
  renderFolders();
}


async function handleFolderSubmit(event) {
  event.preventDefault();
  await api("/api/favorites/folders", {
    method: "POST",
    body: JSON.stringify({
      name: elements.folderName.value.trim(),
      notes: elements.folderNotes.value.trim(),
    }),
  });
  elements.folderForm.reset();
  await loadFolders();
  renderFavorites();
}


async function handleFolderClick(event) {
  const button = event.target.closest("button[data-action]");
  if (!button) return;

  if (button.dataset.action === "filter-folder") {
    state.activeFolderId = button.dataset.folderId;
    renderFolders();
    renderFavorites();
  }

  if (button.dataset.action === "delete-folder") {
    await api(`/api/favorites/folders/${encodeURIComponent(button.dataset.folderId)}`, {method: "DELETE"});
    state.activeFolderId = "all";
    await loadFolders();
    await loadFavorites();
  }
}


async function handleMdFolderSubmit(event) {
  event.preventDefault();
  await loadMarkdownFiles();
}


async function handleMarkdownFileClick(event) {
  const button = event.target.closest("button[data-action='read-md-file']");
  if (!button) return;

  const row = button.closest(".file-row");
  await openMarkdownPath(row.dataset.path);
}


async function openFavoriteMarkdown(itemId) {
  setReaderLoading();
  try {
    const document = await api(`/api/favorites/${encodeURIComponent(itemId)}/markdown`);
    renderDocument(document);
  } catch (error) {
    renderReaderError(error.message);
  }
}


async function openMarkdownPath(path) {
  setReaderLoading();
  try {
    const document = await api(`/api/markdown_files/read?path=${encodeURIComponent(path)}`);
    renderDocument(document);
  } catch (error) {
    renderReaderError(error.message);
  }
}


function setReaderLoading() {
  elements.readerStatus.textContent = "Loading";
  elements.readerPath.textContent = "";
  elements.readerContent.innerHTML = '<div class="empty-state">Opening Markdown...</div>';
}


function renderDocument(document) {
  elements.readerStatus.textContent = "Open";
  elements.readerPath.textContent = document.path;
  elements.readerContent.innerHTML = renderMarkdown(document.content);
}


function renderReaderError(message) {
  elements.readerStatus.textContent = "Error";
  elements.readerPath.textContent = "";
  elements.readerContent.innerHTML = `<div class="empty-state">${escapeHtml(message)}</div>`;
}


function renderMarkdown(markdown) {
  const lines = markdown.split(/\r?\n/);
  const html = [];
  let inList = false;
  let inCode = false;
  let codeLines = [];

  const closeList = () => {
    if (inList) {
      html.push("</ul>");
      inList = false;
    }
  };

  const closeCode = () => {
    html.push(`<pre><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
    codeLines = [];
    inCode = false;
  };

  lines.forEach((line) => {
    if (line.trim().startsWith("```")) {
      if (inCode) {
        closeCode();
      } else {
        closeList();
        inCode = true;
      }
      return;
    }

    if (inCode) {
      codeLines.push(line);
      return;
    }

    if (!line.trim()) {
      closeList();
      return;
    }

    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      closeList();
      const level = heading[1].length;
      html.push(`<h${level}>${escapeHtml(heading[2])}</h${level}>`);
      return;
    }

    const bullet = line.match(/^[-*]\s+(.+)$/);
    if (bullet) {
      if (!inList) {
        html.push("<ul>");
        inList = true;
      }
      html.push(`<li>${escapeHtml(bullet[1])}</li>`);
      return;
    }

    closeList();
    html.push(`<p>${escapeHtml(line)}</p>`);
  });

  closeList();
  if (inCode) closeCode();
  return html.join("");
}


elements.refresh.addEventListener("click", loadFavorites);
elements.list.addEventListener("click", handleFavoriteClick);
elements.list.addEventListener("change", handleFavoriteChange);
elements.folderForm.addEventListener("submit", handleFolderSubmit);
elements.folderList.addEventListener("click", handleFolderClick);
elements.mdFolderForm.addEventListener("submit", handleMdFolderSubmit);
elements.files.addEventListener("click", handleMarkdownFileClick);
elements.useDefaultFolder.addEventListener("click", () => loadMarkdownFiles(state.defaultNotesDir));

await loadConfig();
await loadFolders();
await loadFavorites();
loadMarkdownFiles();
